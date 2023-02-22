# CICD Python for GitLab

![Gitlab_WorkFlow](pic/gitlab_workflow_example.png)
<img src="pic/gitlab_workflow_example_extended.png" alt="My Image" width="400"/>

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
> 1. Modify `/etc/docker/daemon.json` docker config,
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