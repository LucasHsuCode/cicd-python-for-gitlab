# CICD Python for GitLab

<img src="pic/gitlab_workflow_example.png" alt="My Image" width="800"/>
<img src="pic/gitlab_workflow_example2.png" alt="My Image" width="800"/>

<sub>圖片來源: https://docs.gitlab.com/ee/ci/introduction/ </sub>

This is a template project for python.

- [Project Branch Architecture](#project-branch-architecture)
- [Upload To NAS](#upload-to-nas)
- [Create Docker Registry Server](#create-docker-registry-server)
- [GitLab Runner](#gitlab-runner)
- [Coding Style Checker](#coding-style-checker)
- [Unit Tests](#unit-tests)
- [Roadmap](#roadmap)
- [License](#license)

## Project Branch Architecture

```graph
.
+-- main (release branch)
+-- dev2 (develop branch)
```

### Protected branches
1. Create `dev2` branch
2. Go to **Settings > Repository** and expand **Protected branches**
3. Add `dev2` branch to protect it
4. Set **"No One"** in  **"Allowed to push"** of `main` and `dev2` 

### Merge checks

1. Go to **Settings > Repository**
2. Under Merge checks
    - Select the **"Pipelines must succeed"** checkbox
    - Select the **"All threads must be resolved"** checkbox
3. Select Save changes

[Top](#cicd-python-for-gitlab)

# Upload To NAS

Set the mask variables, `NAS_IP, NAS_ACCOUNT, NAS_PASSWORD, NAS_ROOT` into CI/CD.  
And the [scripts](https://192.168.72.6:8443/testgroup/cicd-android-for-gitlab/-/blob/main/.gitlab-ci.yml) will use it.

1. Go to **Settings > CI/CD** and expand **Variables**
2. Click **Add Variable**,
   - Key: `NAS_IP`, Value: `...`, and select the **"Mask variable"** checkbox.
   - Key: `NAS_ACCOUNT`, Value: `...`, and select the **"Mask variable"** checkbox.
   - Key: `NAS_PASSWORD`, Value: `...`, and select the **"Mask variable"** checkbox.
   - Key: `NAS_ROOT`, Value: `...`, and select the **"Mask variable"** checkbox.

[Top](#cicd-python-for-gitlab)

## Create Docker Registry Server 
1. Install [Docker](https://docs.docker.com/engine/install/)
2. Install the Docker image and start the container
    ```bash
    $ export REGISTRY_SERVER_NAME="docker-registry"   
    $ export DOCKER_VOL="docker-registry-volume"
    $ docker volume create $DOCKER_VOL   
    $ docker run -d --name $REGISTRY_SERVER_NAME --restart always -p 5000:5000 \
        -v $DOCKER_VOL:/var/lib/registry registry:2 
    ```
   - [啟動EGISTRY_SERVER_NAME容器指令說明](#command-info)
   - [docker-volume 解釋](#docker-volume)

3. Test Registry Server 
    ```bash
    $ export REGISTRY_IP="192.168.71.213" # Set Server IP
    $ docker run --rm hello-world
    $ docker tag hello-world:latest $REGISTRY_IP:5000/hello-world:latest 
    $ docker push $REGISTRY_IP:5000/hello-world:latest 
    ```
> When execute "docker push ...", but the following error message is shown such as
>
> > The push refers to repository [192.168.71.213:5000/hello-world]  
> Get "https://192.168.71.213:5000/v2/": http: server gave HTTP response to HTTPS client
> 
> 1. 修改 Docker守護程序的不安全註冊表清單中
> 
>   Modify `/etc/docker/daemon.json` docker config,   
>   ```vim
>   {
>     "insecure-registries": ["192.168.182.134:5000"]
>   }
>   ```
> 2. Restart `docker`
>   ```bash
>   $ systemctl restart docker
>   ```

[Top](#cicd-python-for-gitlab)

## GitLab Runner

Run GitLab runner in docker-in-docker (DinD) to make runner can use insecure registry.

1. Install [Docker](https://docs.docker.com/engine/install/)
2. Start the DinD container
    ```bash
    $ export DIND_TAG="local-dind"
    $ export DIND_NAME="local-dind"
    $ export GITLAB_RUNNER_VOL="gitlab-runner-config"
    $ git clone https://cri-gitlab.cri.lab/testgroup/nvidia-dind.git
    $ cd nvidia-dind && docker build -t $DIND_TAG --no-cache . && cd -
    $ docker volume create $GITLAB_RUNNER_VOL
    $ docker run -d --name $DIND_NAME --restart always \
        --privileged --gpus all --shm-size 8g \
        -v $GITLAB_RUNNER_VOL:/etc/gitlab-runner -v /Cache:/Cache \
        $DIND_TAG --insecure-registry $REGISTRY_IP:5000
    ```
3. Start the gitlab runner container in the DinD container
    ```bash
    $ export GITLAB_RUNNER_NAME="gitlab-runner"
    $ docker exec -it $DIND_NAME \
        docker run -d --name $GITLAB_RUNNER_NAME --restart always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /etc/gitlab-runner:/etc/gitlab-runner \
        -v /Cache:/Cache \
        gitlab/gitlab-runner:latest
    ```
4. Obtain URL (`GITLAB_URL`) and registration token (`GITLAB_TOKEN`)
    - Go to **Settings > CI/CD** and expand **Runners**
5. Common Command for Runner
    - Register runner
      > If you need to use Docker-in-Docker (for example, to build a Docker image as part of the CI/CD process) then you
      should also specify the --docker-privileged flag.
      ```bash
      $ export GITLAB_URL="https://cri-gitlab.cri.lab/"
      $ export GITLAB_TOKEN="..."
      $ export RUNNER_NAME="docker-213"
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner register -n --docker-privileged \
              --url $GITLAB_URL --clone-url $GITLAB_URL \
              --registration-token $GITLAB_TOKEN \
              --executor docker \
              --config /etc/gitlab-runner/config.toml \
              --description $RUNNER_NAME \
              --docker-image "docker:stable" \
              --tag-list "docker" \
              --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
              --docker-volumes /Cache:/Cache
      ```
    - Register runner with GPU
      > --docker-gpus ["all", "device=0", "device=1", ...]
      ```bash
      $ export RUNNER_NAME="docker-gpus-213"
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner register -n --docker-privileged \
            --url $GITLAB_URL --clone-url $GITLAB_URL \
            --registration-token $GITLAB_TOKEN \
            --executor docker \
            --config /etc/gitlab-runner/config.toml \
            --description $RUNNER_NAME \
            --docker-image "nvidia/cuda:12.0.0-base-ubuntu20.04" \
            --tag-list "docker-gpus" \
            --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
            --docker-volumes /Cache:/Cache \
            --docker-shm-size 2147483648 --docker-gpus "all" 
      ```
    - Check `config.toml` of GitLab runner
      ```bash
      $ docker exec -it $DIND_NAME cat /etc/gitlab-runner/config.toml
      ```
    - Deregister a Runner
      ```bash
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner unregister --name $RUNNER_NAME
      ```
      > If you have already removed the runner from the GitLab instance then that won’t work and you’ll get an error.
      > However, this can be easily resolved using the following command.
      > ```bash
      > $ docker exec -it $DIND_NAME \
      >    docker exec -it $GITLAB_RUNNER_NAME gitlab-runner verify --delete
      > ```
    - Listing Runners
      ```bash
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner list
      ```
    - Stopping, Starting and Restarting the Runners
      ```bash
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner stop
      ```
      ```bash
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner start
      ```
      ```bash
      $ docker exec -it $DIND_NAME \
          docker exec -it $GITLAB_RUNNER_NAME gitlab-runner restart
      ```

Reference

- https://datawookie.dev/blog/2021/03/install-gitlab-runner-with-docker/
- https://github.com/Extrality/nvidia-dind

> When registering runner, but the following error message is shown such as
>
> - Error 1
>
>   > ERROR: Registering runner... failed runner=GR1348941vx8VF3qb status=couldn't execute POST
>   > against https://cri-gitlab.cri.lab/api/v4/runners: Post "https://cri-gitlab.cri.lab/api/v4/runners": x509:
>   > certificate is valid for synology, not cri-gitlab.cri.lab  
>   > PANIC: Failed to register the runner.
>
>   Replacing `https` with `http` solves the problem.
>
> - Error 2
>
>   > ERROR: Registering runner... failed runner=xxx status=couldn't execute POST
>   > against https://192.168.72.6:8443/api/v4/runners: Post "https://192.168.72.6:8443/api/v4/runners": x509: cannot
>   > validate certificate for 192.168.72.6 because it doesn't contain any IP SANs  
>   > PANIC: Failed to register the runner.
>
>   Execute following command,
>
>   ```bash
>   $ export GITLAB_SERVER="cri-gitlab.cri.lab"
>   $ export GITLAB_PORT="443"
>   $ export GITLAB_URL=https://${GITLAB_SERVER}:${GITLAB_PORT}/
>   $ export GITLAB_TOKEN="GR1348941kEMq3t7MQ1n1vMgUMEys"
>   $ export CERTIFICATE=/etc/gitlab-runner/certs/${GITLAB_SERVER}.crt
>   $ export RUNNER_NAME="docker213"
>   $ 
>   $ # Create the certificates hierarchy expected by gitlab
>   $ docker exec -it $DOCKER_NAME mkdir -p $(dirname "$CERTIFICATE")
>   $
>   $ # Get the certificate in PEM format and store it
>   $ docker exec -it $DOCKER_NAME bash -c 'openssl s_client -connect '"${GITLAB_SERVER}:${GITLAB_PORT}"' -showcerts </dev/null 2>/dev/null | sed -e'"'"'/-----BEGIN/,/-----END/!d'"' | tee \"$CERTIFICATE\" >/dev/null"
>   $ # or
>   $ docker exec -it $DOCKER_NAME bash -c "openssl s_client -showcerts -connect ${GITLAB_SERVER}:${GITLAB_PORT} -servername ${GITLAB_SERVER} < /dev/null 2>/dev/null | openssl x509 -outform PEM > $CERTIFICATE"
>   $ 
>   $ # Check *.crt
>   $ docker exec -it $DOCKER_NAME bash -c "echo | openssl s_client -CAfile $CERTIFICATE -connect ${GITLAB_SERVER}:${GITLAB_PORT} -servername ${GITLAB_SERVER}"
>   $
>   $ # Register your runner
>   $ docker exec -it $DIND_NAME \
>       docker exec -it $GITLAB_RUNNER_NAME gitlab-runner register -n --docker-privileged \
>       --url $GITLAB_URL --clone-url $GITLAB_URL \
>       --registration-token $GITLAB_TOKEN \
>       --executor docker \
>       --config /etc/gitlab-runner/config.toml \
>       --description $RUNNER_NAME \
>       --docker-image "docker:stable" \
>       --tag-list "docker" \
>       --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
>       --docker-volumes /Cache:/Cache \
>       --tls-ca-file $CERTIFICATE
>   ``` 
>
> Reference:
> - https://stackoverflow.com/questions/44458410/gitlab-ci-runner-ignore-self-signed-certificate
> - https://docs.gitlab.com/runner/configuration/tls-self-signed.html
> - https://gitlab.com/gitlab-org/gl-openshift/gitlab-runner-operator/-/issues/56

[Top](#cicd-python-for-gitlab)

## Coding Style Checker

- Install `pylint` and `flake8`
   ```bash
   $ pip install flake8 pylint pylint-pytest
   ``` 
- Check source code
   ```bash
   $ flake8 examples/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
   $ pylint examples/ 
   ``` 
- Check test code
   ```bash
   $ flake8 tests/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
   $ pylint --load-plugins pylint_pytest tests/
   ```

- Modified **".pylintrc"** can adjust coding style format for `pylint`

## Unit Tests

```bash
$ pytest tests/tests.py --doctest-modules --cov=. --cov-report=xml --cov-report=html
```

[Top](#cicd-python-for-gitlab)

## Roadmap

- [x] Create GitLab runner
- [x] Add `CI/CD`
- [ ] Create `docker` environment
- [ ] Create `conda` environment
- [x] Add coding style checker
- [x] Add unit tests
- [X] Set coding style checker in `CI/CD`
- [X] Set unit tests in `CI/CD`
- [X] Add GPU inference in `CI/CD`
- [ ] Upload to NAS

[Top](#cicd-python-for-gitlab)

## License

[MIT License](LICENSE)

[Top](#cicd-python-for-gitlab)


## Docker-Volume 
[Create Docker Registry Server](#create-docker-registry-server)
```bash
Docker Volume 是 Docker 容器用來儲存資料的一種機制。它可以讓 Docker 容器中的資料在容器被刪除或重啟後不會丟失，並且可以跨容器共用。
 
Docker Volume 可以被視為一個磁碟區，用來儲存容器中的資料。Docker 容器可以將指定的目錄掛載到 Docker Volume 上，這樣容器中的資料就可以被儲存在 Docker Volume 中。Docker Volume 可以被用來儲存任何類型的資料，包括應用程式數據、資料庫資料、設定檔、日誌等等。

使用 Docker Volume 的好處有以下幾點：

  1. 容器與資料分離：Docker Volume 可以讓容器和資料分離，讓容器被刪除或重啟時不會丟失資料。
  2. 容器共用資料：多個容器可以共用同一個 Docker Volume，這樣它們就可以存取同樣的資料。
  3. 方便管理：Docker Volume 可以通過 Docker CLI 或 Docker API 方便地管理，可以進行備份、恢復、移動等操作。

在 Docker 中，可以使用以下指令來管理 Docker Volume：

  $ docker volume create：建立一個新的 Docker Volume。
  $ docker volume ls：列出所有的 Docker Volume。
  $ docker volume rm：刪除一個 Docker Volume。
  $ docker volume inspect：檢視一個 Docker Volume 的詳細資訊。

在運行 Docker 容器時，可以使用 -v 參數來掛載 Docker Volume。例如，以下指令可以將本地機器的 /data 目錄掛載到容器中的 /var/lib/mysql 目錄：

  $ docker run -v /data:/var/lib/mysql mysql:latest

這樣容器中的 MySQL 數據就會被儲存在 /data 目錄中，即使容器被刪除或重啟，數據也不會丟失。
```
## Command-Info 
[Create Docker Registry Server](#create-docker-registry-server)
```bash
$ docker run -d --name $REGISTRY_SERVER_NAME --restart always -p 5000:5000 -v $DOCKER_VOL:/var/lib/registry registry:2

這個指令是在運行 Docker 容器，並啟動一個名為 $REGISTRY_SERVER_NAME 的 Docker 容器，
它的映像是 registry:2。下面是指令中使用的各個選項的詳細說明：

  -d ：運行 Docker 容器的模式，此選項表示以“分離模式”運行，也就是在背景運行容器。
  --name $REGISTRY_SERVER_NAME ：容器的名稱，即為環境變數 $REGISTRY_SERVER_NAME 的值。
  -restart always ：表示當 Docker 容器停止運行時，自動重啟容器。
  -p 5000:5000 ：表示將容器內部的 5000 端口映射到主機上的 5000 端口。
  -v $DOCKER_VOL:/var/lib/registry ：表示將環境變數 $DOCKER_VOL 指定的卷掛載到容器內的 
  /var/lib/registry 目錄下，卷是 Docker 中一個常用的特性，可以用來在容器和主機之間共享數據。
  
  registry:2 ：表示 Docker Hub 上的 registry 映像，並且是 registry 的版本號為 2 的版本。
總體而言，這個指令的作用是在本地機器上運行一個 Docker 容器，並在其中運行 Docker Registry 服務，
使得本地機器可以作為私有的 Docker 映像倉庫，方便映像的存儲和分享。

當Docker在本機找不到指定的鏡像時，會嘗試在Docker官方鏡像庫（Docker Hub）上下載該鏡像。因此，當您運行 docker run 命令時，如果 Docker 在本地找不到鏡像，它會從 Docker Hub 上下載相應的鏡像。
在您的情況下，Docker Hub 上有 registry:2 鏡像，因此當您運行 docker run registry:2 命令時，Docker 會從 Docker Hub 下載 registry:2 鏡像。下載完成後，該鏡像會被保存在本地Docker中。
如果您沒有看到任何錯誤訊息，而是看到一個長的十六進位碼，就表示容器已經成功啟動了。


$ export REGISTRY_IP="192.168.71.213" # Set Server IP
$ docker run --rm hello-world
$ docker tag hello-world:latest $REGISTRY_IP:5000/hello-world:latest 
$ docker push $REGISTRY_IP:5000/hello-world:latest 

這組指令是用來將 hello-world 這個 Docker 鏡像推送到 $REGISTRY_IP 主機上的 Docker Registry。

$ export REGISTRY_IP="192.168.71.213": 設定 Docker Registry 的主機 IP。
$ docker run --rm hello-world: 執行 hello-world 這個 Docker 鏡像，並在執行完畢後立即刪除容器。
$ docker tag hello-world:latest $REGISTRY_IP:5000/hello-world:latest: 將本機上的 hello-world 鏡像打標籤，並指定目標標籤的名稱為 $REGISTRY_IP:5000/hello-world:latest。這個指令是為了將 hello-world 鏡像推送到 Docker Registry 上，因此必須將鏡像的名稱修改成 <registry_host>:<registry_port>/<image_name>:<tag> 的形式。
$ docker push $REGISTRY_IP:5000/hello-world:latest: 將打好標籤的 hello-world 鏡像推送到 Docker Registry 上。
這些指令的執行流程大致如下：

首先，使用 export 指令設定 Docker Registry 的主機 IP。
接著，使用 docker run 指令下載並執行 hello-world 鏡像，這是為了確保本機已經存在 hello-world 鏡像。
接著，使用 docker tag 指令將本機上的 hello-world 鏡像打標籤，並將標籤改為 <registry_host>:<registry_port>/<image_name>:<tag> 的形式。這是為了將鏡像推送到 Docker Registry 上。
最後，使用 docker push 指令將打好標籤的 hello-world 鏡像推送到 Docker Registry 上。
可以使用以下指令列出 Docker Registry 上的 images
$ docker images $REGISTRY_IP:5000/*
```
