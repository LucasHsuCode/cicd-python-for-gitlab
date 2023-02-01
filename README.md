# CICD Python for GitLab

This is a template project for python.

- [Project Branch Architecture](#project-branch-architecture)
- [GitLab Runner](#gitlab-runner)
- [Coding Style Checker](#coding-style-checker)
- [Unit Tests](#unit-tests)
- [Roadmap](#roadmap)
- [License](#license)

## Project Branch Architecture

```graph
.
+-- main
+-- dev2
```

- main: release branch
- dev2: develop branch
  1. Create `dev2` branch
  2. Go to **Settings > Repository** and expand **Protected branches**
  3. Add `dev2` branch to protect it

### Merge checks

1. Go to **Settings > Repository**
2. Under Merge checks
    - Select the **"Pipelines must succeed"** checkbox
    - Select the **"All threads must be resolved"** checkbox
3. Select Save changes

[Top](#cicd-python-for-gitlab)

## GitLab Runner

1. Install [Docker](https://docs.docker.com/engine/install/)
2. Install the Docker image and start the container
    ```bash
    $ export DOCKER_NAME="gitlab-runner"
    $ docker volume create gitlab-runner-config
    $ docker run -d --name $DOCKER_NAME --restart always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v gitlab-runner-config:/etc/gitlab-runner \
        gitlab/gitlab-runner:latest
    ```
3. Obtain URL (`GITLAB_URL`) and registration token (`GITLAB_TOKEN`)
    - Go to **Settings > CI/CD** and expand **Runners**
4. Common Command for Runner
    - Register runner
      > If you need to use Docker-in-Docker (for example, to build a Docker image as part of the CI/CD process) then you
      should also specify the --docker-privileged flag.
      ```bash
      $ export GITLAB_URL="https://cri-gitlab.cri.lab/"
      $ export GITLAB_TOKEN="GR1348941vx8VF3qbFWX9xLdscFJL"
      $ export RUNNER_NAME="docker213"
      $ docker exec -it $DOCKER_NAME gitlab-runner register -n --docker-privileged \
          --url $GITLAB_URL \
          --registration-token $GITLAB_TOKEN \
          --executor docker \
          --config /etc/gitlab-runner/config.toml \
          --description $RUNNER_NAME \
          --docker-image "docker:latest" \
          --tag-list "docker" \
          --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
          --docker-disable-cache=true 
      ```
    - Deregister a Runner
      ```bash
      $ docker exec -it $DOCKER_NAME gitlab-runner unregister --name $RUNNER_NAME
      ```
      > If you have already removed the runner from the GitLab instance then that won’t work and you’ll get an error.
      However, this can be easily resolved using the following command.
      ```bash
      $ docker exec -it gitlab-runner gitlab-runner verify --delete
      ```
    - Listing Runners
      ```bash
      $ docker exec -it $DOCKER_NAME gitlab-runner list
      ```
    - Stopping, Starting and Restarting the Runners
      ```bash
      $ docker exec -it $DOCKER_NAME gitlab-runner stop
      ```
      ```bash
      $ docker exec -it $DOCKER_NAME gitlab-runner start
      ```
      ```bash
      $ docker exec -it $DOCKER_NAME gitlab-runner restart
      ```

Reference

- https://datawookie.dev/blog/2021/03/install-gitlab-runner-with-docker/

> When registering runner, but the following error message is shown such as
>
> - Error 1
    >   > ERROR: Registering runner... failed runner=GR1348941vx8VF3qb status=couldn't execute POST
    > > against https://cri-gitlab.cri.lab/api/v4/runners: Post "https://cri-gitlab.cri.lab/api/v4/runners": x509:
    > > certificate is valid for synology, not cri-gitlab.cri.lab  
    > > PANIC: Failed to register the runner.
    >
    >   Replacing `https` with `http` solves the problem.
>
> - Error 2
    >   > ERROR: Registering runner... failed runner=xxx status=couldn't execute POST
    > > against https://192.168.72.6:8443/api/v4/runners: Post "https://192.168.72.6:8443/api/v4/runners": x509: cannot
    > > validate certificate for 192.168.72.6 because it doesn't contain any IP SANs  
    > > PANIC: Failed to register the runner.
    >
    >   Execute following command,
    >
    >   ```bash
>   $ export GITLAB_SERVER="cri-gitlab.cri.lab"
>   $ export GITLAB_PORT="443"
>   $ export GITLAB_URL=https://${GITLAB_SERVER}:${GITLAB_PORT}/
>   $ export GITLAB_TOKEN="GR1348941vx8VF3qbFWX9xLdscFJL"
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
>   $ docker exec -it $DOCKER_NAME gitlab-runner register -n --docker-privileged \
>         --url $GITLAB_URL \
>         --registration-token $GITLAB_TOKEN \
>         --tls-ca-file $CERTIFICATE \
>         --executor docker \
>         --config /etc/gitlab-runner/config.toml \
>         --description $RUNNER_NAME \
>         --docker-image "docker:latest" \
>         --tag-list "docker" \
>         --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
>         --docker-disable-cache=true 
>   ```  
>
> Reference:
> - https://stackoverflow.com/questions/44458410/gitlab-ci-runner-ignore-self-signed-certificate
> - https://docs.gitlab.com/runner/configuration/tls-self-signed.html
> - https://gitlab.com/gitlab-org/gl-openshift/gitlab-runner-operator/-/issues/56
>

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

## Unit Tests

```bash
$ pytest tests/tests.py --doctest-modules --cov=. --cov-report=xml --cov-report=html
```

[Top](#cicd-python-for-gitlab)

## Roadmap

- [x] Create GitLab runner
- [x] Add `CI/CD`
- [ ] Create `docker` environment
- [x] Build coding style checker for python
- [x] Build unit tests for CI/CD

[Top](#cicd-python-for-gitlab)

## License

[MIT License](LICENSE)

[Top](#cicd-python-for-gitlab)