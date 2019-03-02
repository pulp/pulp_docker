#!/usr/bin/env sh
set -v

export COMMIT_MSG=$(git show HEAD^2 -s)
export PULP_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/pulp\/pulpcore\/pull\/(\d+)' | awk -F'/' '{print $7}')
export PULP_PLUGIN_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/pulp\/pulpcore-plugin\/pull\/(\d+)' | awk -F'/' '{print $7}')
export PULP_SMASH_PR_NUMBER=$(echo $COMMIT_MSG | grep -oP 'Required\ PR:\ https\:\/\/github\.com\/PulpQE\/pulp-smash\/pull\/(\d+)' | awk -F'/' '{print $7}')

pip install -r test_requirements.txt

cd .. && git clone https://github.com/pulp/pulpcore.git

if [ -n "$PULP_PR_NUMBER" ]; then
  pushd pulpcore
  git fetch origin +refs/pull/$PULP_PR_NUMBER/merge
  git checkout FETCH_HEAD
  popd
fi

pip install -e ./pulpcore[postgres]

git clone https://github.com/pulp/pulpcore-plugin.git

if [ -n "$PULP_PLUGIN_PR_NUMBER" ]; then
  pushd pulpcore-plugin
  git fetch origin +refs/pull/$PULP_PLUGIN_PR_NUMBER/merge
  git checkout FETCH_HEAD
  popd
fi

pip install -e ./pulpcore-plugin

if [ -n "$PULP_SMASH_PR_NUMBER" ]; then
  pip uninstall -y pulp-smash
  git clone https://github.com/PulpQE/pulp-smash.git
  pushd pulp-smash
  git fetch origin +refs/pull/$PULP_SMASH_PR_NUMBER/merge
  git checkout FETCH_HEAD
  popd
  pip install -e ./pulp-smash
fi

# Install Podman client
sudo add-apt-repository -y ppa:projectatomic/ppa
sudo apt-get update -y
sudo apt-get install -y podman

# Configure podman for insecure registry
sudo bash -c 'cat << EOF > /etc/containers/registries.conf
[registries.search]
registries = ["docker.io", "registry.fedoraproject.org", "quay.io", "registry.access.redhat.com", "registry.centos.org"]

[registries.insecure]
registries = ["localhost:8080"]

[registries.block]
registries = []
EOF'

# podman on Travis is asking manual creation of one more file
sudo bash -c 'cat << EOF > /etc/containers/policy.json
{
    "default": [
        {
            "type": "insecureAcceptAnything"
        }
    ],
    "transports":
        {
            "docker-daemon":
                {
                    "": [{"type":"insecureAcceptAnything"}]
                }
        }
}
EOF'

# outputs podman info
sudo podman info

cd pulp_docker
pip install -e .
