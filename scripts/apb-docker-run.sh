# Script for running apb with a container.
# Recommended to copy this to somewhere in your PATH as "apb"
APB_IMAGE=${APB_IMAGE:-docker.io/ansibleplaybookbundle/apb-tools:canary}
echo "Running APB image: ${APB_IMAGE}"

if ! [[ -z "${DOCKER_CERT_PATH}" ]] && [[ ${DOCKER_CERT_PATH} = *"minishift"* ]]; then
  IS_MINISHIFT=true
  echo "Targetting minishift host: ${DOCKER_HOST}"
fi

if [[ $IS_MINISHIFT = true ]]; then
  # If targetting minishift, there are some unique issues with using the apb
  # container. Need to capture the minishift docker-env vars, unset them for the
  # purposes of this command, and pass them through to the docker container along
  # with mounting the minishift docker certs.
  # The minishift docker-env must be unset so the apb container is run by the *host*
  # daemon instead of the minishift daemon. However, It will still be configured
  # to operate on the minishift registry. This is required, as the volume mounts
  # must be mounted into the apb container from the host system.
  # If the minishift daemon is used, they will be empty mounts.
  MINISHIFT_DOCKER_CERT_SRC="${DOCKER_CERT_PATH}"
  MINISHIFT_DOCKER_CERT_DEST="/var/run/minishift-certs"
  MINISHIFT_DOCKER_HOST="${DOCKER_HOST}"

  unset DOCKER_TLS_VERIFY
  unset DOCKER_HOST
  unset DOCKER_CERT_PATH

  docker run --rm --privileged \
    -v $PWD:/mnt -v $HOME/.kube:/.kube \
    -v $MINISHIFT_DOCKER_CERT_SRC:$MINISHIFT_DOCKER_CERT_DEST \
    -e DOCKER_TLS_VERIFY="1" \
    -e DOCKER_HOST="${MINISHIFT_DOCKER_HOST}" \
    -e DOCKER_CERT_PATH="${MINISHIFT_DOCKER_CERT_DEST}" \
    -e MINISHIFT_REGISTRY=$(minishift openshift registry) \
    -u $UID $APB_IMAGE "$@"
else
  docker run --rm --privileged \
    -v $PWD:/mnt -v $HOME/.kube:/.kube \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -u $UID $APB_IMAGE "$@"
fi
