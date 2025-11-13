# Update the ip for sshconfigdefinition in ssh config file
# Create remote-dev context for docker
#   docker context create remote-dev --docker "ssh://sshconfigdefinition"
# Set the docker context to remote-dev
#   docker context use remote-dev
# Don't forget to set the docker context to the default when done

# sudo apt update; sudo apt install -y nano htop

echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGfSWokLXy/QmagyiG6hjPG/wxFKmmgyOk65pLvfNizZ" > ~/.ssh/authorized_keys

sudo usermod -aG docker $USER
newgrp docker
