from commands.base import Command, command
from errors import Result
from settings import Settings
import requests
from typing import Optional, Dict, Any, List
import logging
import subprocess
import platform
import os



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
VLLM_MODEL = "Qwen/QwQ-32B"
VLLM_MAX_MODEL_LEN = 32768 # 131072
VLLM_TENSOR_PARALLEL_SIZE = 2

STARTUP_SCRIPTS = {
  "vllm": [
    # Add http and https to ufw
    "ufw allow http",
    "ufw allow https",

    # Create network for containers
    "docker network create vllm-network || true",

    # Create Traefik config directories
    "mkdir -p ~/traefik/config ~/traefik/acme ~/traefik/logs",

    # Create Traefik static config
    'echo "api:"                                                                          > ~/traefik/config/traefik.yml',
    'echo "  dashboard: true"                                                            >> ~/traefik/config/traefik.yml',
    'echo "  debug: false"                                                               >> ~/traefik/config/traefik.yml',
    'echo "  insecure: true"                                                             >> ~/traefik/config/traefik.yml',
    'echo "  disabledashboardad: true"                                                   >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "log:"                                                                         >> ~/traefik/config/traefik.yml',
    'echo "  level: \\"INFO\\""                                                          >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "ping: {{}}"                                                                   >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "providers:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "  docker:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "    endpoint: \\"unix:///var/run/docker.sock\\""                              >> ~/traefik/config/traefik.yml',
    'echo "    exposedByDefault: false"                                                  >> ~/traefik/config/traefik.yml',
    # 'echo "  file:"                                                                    >> ~/traefik/config/traefik.yml',
    # 'echo "    filename: \\"/etc/traefik/services.yaml\\""                             >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "accessLog:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "  filePath: \\"/logs/access.log\\""                                           >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "entryPoints:"                                                                 >> ~/traefik/config/traefik.yml',
    'echo "  web:"                                                                       >> ~/traefik/config/traefik.yml',
    'echo "    address: \\":80\\""                                                       >> ~/traefik/config/traefik.yml',
    'echo "    http:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      redirections:"                                                          >> ~/traefik/config/traefik.yml',
    'echo "        entryPoint:"                                                          >> ~/traefik/config/traefik.yml',
    'echo "          to: websecure"                                                      >> ~/traefik/config/traefik.yml',
    'echo "          scheme: https"                                                      >> ~/traefik/config/traefik.yml',
    'echo "  websecure:"                                                                 >> ~/traefik/config/traefik.yml',
    'echo "    address: \\":443\\""                                                      >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "certificatesResolvers:"                                                       >> ~/traefik/config/traefik.yml',
    'echo "  letsencrypt:"                                                               >> ~/traefik/config/traefik.yml',
    'echo "    acme:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      email: \\"{email}\\""                                                   >> ~/traefik/config/traefik.yml',
    'echo "      caServer: \\"https://acme-v02.api.letsencrypt.org/directory\\""         >> ~/traefik/config/traefik.yml',
    'echo "      storage: \\"/acme/letsencrypt.json\\""                                  >> ~/traefik/config/traefik.yml',
    'echo "      tlsChallenge: {{}}"                                                     >> ~/traefik/config/traefik.yml',
    'echo "  staging:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "    acme:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      email: \\"{email}\\""                                                   >> ~/traefik/config/traefik.yml',
    'echo "      caServer: \\"https://acme-staging-v02.api.letsencrypt.org/directory\\"" >> ~/traefik/config/traefik.yml',
    'echo "      storage: \\"/acme/staging.json\\""                                      >> ~/traefik/config/traefik.yml',
    'echo "      tlsChallenge: {{}}"                                                     >> ~/traefik/config/traefik.yml',
    'echo "  zerossl:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "    acme:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      email: \\"{email}\\""                                                   >> ~/traefik/config/traefik.yml',
    'echo "      caServer: \\"https://acme.zerossl.com/v2/DV90\\""                       >> ~/traefik/config/traefik.yml',
    'echo "      storage: \\"/acme/zerossl.json\\""                                      >> ~/traefik/config/traefik.yml',
    'echo "      httpChallenge:"                                                         >> ~/traefik/config/traefik.yml',
    'echo "        entryPoint: web"                                                      >> ~/traefik/config/traefik.yml',
    'echo "      eab:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "        kid: \\"{eab_kid}\\""                                                 >> ~/traefik/config/traefik.yml',
    'echo "        hmacEncoded: \\"{eab_hmac_encoded}\\""                                >> ~/traefik/config/traefik.yml',

    # Start VLLM container
    "sudo docker run -d --name vllm --network vllm-network --runtime nvidia --ipc=host --gpus all " +
    "-v ~/.cache/huggingface:/root/.cache/huggingface " +
    "-e HUGGING_FACE_HUB_TOKEN={hf_token} " +
    "-l 'traefik.enable=true' " +
    "-l 'traefik.http.routers.vllm.rule=Host(`{subdomain}.{zone}`)' " +
    "-l 'traefik.http.routers.vllm.entrypoints=websecure' " +
    "-l 'traefik.http.routers.vllm.tls.certresolver=letsencrypt' " +
    "-l 'traefik.http.services.vllm.loadbalancer.server.port=8000' " +
    f"vllm/vllm-openai:latest --model {VLLM_MODEL} --max-model-len {VLLM_MAX_MODEL_LEN} --tensor-parallel-size {VLLM_TENSOR_PARALLEL_SIZE}",

    # Start Traefik container
    "sudo docker run -d --name traefik --network vllm-network " +
    "-v /var/run/docker.sock:/var/run/docker.sock:ro " +
    "-v ~/traefik/config:/etc/traefik " +
    "-v ~/traefik/acme:/acme " +
    "-v ~/traefik/logs:/logs " +
    "-p 80:80 -p 443:443 " +
    # "-p 8080:8080 " +  # Added port for Traefik dashboard
    "traefik:latest",

    # Start DDNS updater container
    "sudo docker run -d --name ddns-updater " +
    "-e ZONE={zone} " +
    "-e SUBDOMAIN={subdomain} " +
    "-e API_KEY={cloudflare_token} " +
    "oznu/cloudflare-ddns:latest",

    # Print success message
    "echo 'Containers deployed successfully. VLLM will be available at https://{subdomain}.{zone} once DNS propagates'"
  ],
  "test": [
    "echo 'foxes will rule the world!' > /home/Ubuntu/test.txt"
  ],
  "docker-remote": [
    # Install dependencies
    "sudo apt update",
    "sudo apt install -y nano htop",

    # Add SSH key
    "echo ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGfSWokLXy/QmagyiG6hjPG/wxFKmmgyOk65pLvfNizZ > ~/.ssh/authorized_keys",

    # Add user to docker group
    "sudo usermod -aG docker $USER",

    # # Restart system
    # "sudo shutdown -r now",
  ],
  "ddns": [
    "docker run -d --name ddns-updater " +
    "-e ZONE={zone} " +
    "-e SUBDOMAIN={subdomain} " +
    "-e API_KEY={cloudflare_token} " +
    "oznu/cloudflare-ddns:latest",
  ]
}

SSH_CONNECT_TIMEOUT = "30"  # Timeout in seconds for SSH connection attempts

# GPU VRAM in GB for each GPU type
GPU_VRAM = {
  "a6000": 48,    # RTX A6000
  "h100": 80,     # H100
  "l40": 48,      # NVIDIA L40
  "a5000": 24,    # RTX A5000
  "l40s": 48,     # L40S
  "a100": 80,     # A100
  "a30": 24,      # NVIDIA A30
  "h100_nvl": 94  # H100 NVL
}



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class MassedComputeCommand(Command):

  @command(
    path=["list", "instances"],
    description="List running instances",
    help_text="List all running instances"
  )
  def list_instances(self, settings: Settings) -> str:
    """List all running instances"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)
      instances = api.get_instances()

      # Print formatted table
      output = []
      for line in format_instances_table(instances):
        print(line)
        output.append(line)

      return "\n".join(output)

    except Exception as e:
      error_msg = f"Error listing instances: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["list", "gpus"],
    description="List available GPU configurations",
    help_text="List available GPU configurations with optional sorting",
    parameters={
      "type": "object",
      "properties": {
        "sort_by": {
          "type": "string",
          "description": "Sort option (price/p, vram/v, value/val, available/a). Add '-' prefix for reverse sort."
        }
      }
    }
  )
  def list_gpus(self, settings: Settings, sort_by: str = None) -> str:
    """List available GPU configurations with optional sorting"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)
      inventory = api.get_gpu_inventory()

      # Format and print GPU inventory
      output = [
        "\nAvailable GPU Configurations:",
        "-" * 122,  # Increased width
        f"{'Product':<25} {'Description':<25} {'VRAM':<10} {'Price/Hr':<10} {'$/Hr/GB':<10} {'Available':<10}",
        "-" * 122  # Increased width
      ]

      # Prepare data for sorting
      gpu_data = []
      for product_info in inventory.values():
        instance_type = product_info.get('instance_type', {})
        name = instance_type.get('name', 'N/A')
        desc = instance_type.get('description', 'N/A')
        price = instance_type.get('price_cents_per_hour', 0) / 100
        capacity = product_info.get('capacity_available', 0)

        # Skip if sorting by available and capacity is 0
        if sort_by and sort_by.lstrip('-') in ['available', 'a'] and capacity == 0:
          continue

        # Calculate VRAM and $/Hr/GB if possible
        vram_amount = 0
        price_per_gb = 0
        vram_str = "N/A"
        price_per_gb_str = "N/A"

        for gpu_type, vram in GPU_VRAM.items():
          if gpu_type.lower() in name.lower():
            # Extract multiplier from name (1x, 2x, etc)
            multiplier = 1
            if "gpu_" in name.lower() and "x_" in name.lower():
              try:
                multiplier = int(name.split("x_")[0].split("gpu_")[1])
              except ValueError:
                pass
            vram_amount = vram * multiplier
            vram_str = f"{vram_amount}GB"
            if vram_amount > 0:
              price_per_gb = price/vram_amount
              price_per_gb_str = f"${price_per_gb:.3f}"
            break

        gpu_data.append({
          'name': name,
          'desc': desc,
          'vram': vram_amount,
          'vram_str': vram_str,
          'price': price,
          'price_per_gb': price_per_gb,
          'price_per_gb_str': price_per_gb_str,
          'capacity': capacity
        })

      # Sort data if sort parameter is provided
      if sort_by:
        reverse = True if sort_by.startswith('-') else False
        sort_by = sort_by.lstrip('-')

        sort_key = None
        if sort_by in ['price', 'p']:
          sort_key = 'price'
        elif sort_by in ['vram', 'v']:
          sort_key = 'vram'
        elif sort_by in ['value', 'val']:
          sort_key = 'price_per_gb'
        elif sort_by in ['available', 'a']:
          sort_key = 'capacity'

        if sort_key:
          gpu_data.sort(key=lambda x: x[sort_key], reverse=reverse)
        else:
          sort_help = [
            f"\nUnknown sort parameter: {sort_by}",
            "Available sort options:",
            "  price, p       - Sort by price per hour",
            "  vram, v        - Sort by total VRAM",
            "  value, val     - Sort by $/Hr/GB",
            "  available, a   - Sort by available capacity (hides unavailable)",
            "Add '-' prefix for reverse sort (e.g., -price)"
          ]
          for line in sort_help:
            print(line)
            output.append(line)
          return "\n".join(output)

      # Print sorted data
      for gpu in gpu_data:
        line = f"{gpu['name'][:25]:<25} {gpu['desc'][:25]:<25} {gpu['vram_str']:<10} " \
               f"${gpu['price']:<9.2f} {gpu['price_per_gb_str']:<10} {gpu['capacity']:<10}"
        print(line)
        output.append(line)

      return "\n".join(output)

    except Exception as e:
      error_msg = f"Error listing GPU inventory: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["list", "images"],
    description="List available VM images",
    help_text="List all available VM images that can be deployed"
  )
  def list_images(self, settings: Settings) -> str:
    """List all available VM images"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)
      images = api.get_images()

      # Print formatted table
      output = []
      for line in format_images_table(images):
        print(line)
        output.append(line)

      return "\n".join(output)

    except Exception as e:
      error_msg = f"Error listing images: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["deploy", "cheapest"],
    description="Deploy cheapest available GPU instance",
    help_text="Deploy the cheapest available GPU instance with specified image and name",
    parameters={
      "type": "object",
      "properties": {
        "image_id": {
          "type": "integer",
          "description": "ID of the image to deploy"
        },
        "instance_name": {
          "type": "string",
          "description": "Name for the new instance"
        },
        "startup_script": {
          "type": "string",
          "description": "Optional name of startup script to run ('vllm', 'test', etc.)"
        },
        "ssh_keys": {
          "type": "string",
          "description": "Optional space-separated list of SSH keys to add to the instance"
        }
      },
      "required": ["image_id", "instance_name"]
    }
  )
  def deploy_cheapest_instance(self, settings: Settings, image_id: int, instance_name: str,
                              startup_script: str = None, ssh_keys: str = None) -> str:
    """Deploy the cheapest available GPU instance"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)

      script = None
      ssh_key_list = []

      # Parse startup script if provided
      if startup_script:
        script_name = startup_script.lower()
        # Parse any extra parameters (we'd need to handle those separately in a real implementation)
        extra_params = {}

        script = get_startup_script(script_name, settings, extra_params)
        if script is None:
          msg = f"Unknown startup script: {script_name}\nAvailable scripts: {', '.join(STARTUP_SCRIPTS.keys())}"
          print(msg)
          return msg

      # Parse SSH keys if provided
      if ssh_keys:
        ssh_key_list = ssh_keys.split()

      response = api.deploy_cheapest_instance(
        image_id,
        instance_name,
        script,
        ssh_key_list
      )

      instance_uuid = response.get('response')
      output = [f"Deployed instance with UUID: {instance_uuid}"]

      if ssh_key_list:
        output.append("Added SSH keys:")
        for key in ssh_key_list:
          output.append(f"  - {key}")

      result = "\n".join(output)

      return result

    except Exception as e:
      error_msg = f"Error: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["deploy", "specific"],
    description="Deploy a specific GPU instance type",
    help_text="Deploy a specific GPU instance with specified image, name, and product type",
    parameters={
      "type": "object",
      "properties": {
        "image_id": {
          "type": "integer",
          "description": "ID of the image to deploy"
        },
        "instance_name": {
          "type": "string",
          "description": "Name for the new instance"
        },
        "product_name": {
          "type": "string",
          "description": "Name of the specific product to deploy"
        },
        "startup_script": {
          "type": "string",
          "description": "Optional name of startup script to run ('vllm', 'test', etc.)"
        },
        "ssh_keys": {
          "type": "string",
          "description": "Optional space-separated list of SSH keys to add to the instance"
        }
      },
      "required": ["image_id", "instance_name", "product_name"]
    }
  )
  def deploy_specific_instance(self, settings: Settings, image_id: int, instance_name: str,
                              product_name: str, startup_script: str = None, ssh_keys: str = None) -> str:
    """Deploy a specific GPU instance"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)

      # Convert product name to lowercase for case-insensitive matching
      product_name_lower = product_name.lower()

      # Verify the product exists (case-insensitive)
      inventory = api.get_gpu_inventory()
      matching_products = [
        info['instance_type']['name']
        for info in inventory.values()
        if info['instance_type']['name'].lower() == product_name_lower
      ]

      if not matching_products:
        output = [f"Error: Invalid product name '{product_name}'", "\nAvailable products:"]
        for info in inventory.values():
          name = info['instance_type']['name']
          desc = info['instance_type']['description']
          output.append(f"  {name}: {desc}")
        print("\n".join(output))
        return "\n".join(output)

      # Use the correct casing from the inventory
      product_name = matching_products[0]

      script = None
      ssh_key_list = []

      # Parse startup script if provided
      if startup_script:
        script_name = startup_script.lower()
        script = get_startup_script(script_name, settings)
        if script is None:
          msg = f"Unknown startup script: {script_name}\nAvailable scripts: {', '.join(STARTUP_SCRIPTS.keys())}"
          print(msg)
          return msg

      # Parse SSH keys if provided
      if ssh_keys:
        ssh_key_list = ssh_keys.split()

      try:
        response = api.deploy_specific_instance(
          image_id,
          product_name,
          instance_name,
          script,
          ssh_key_list
        )

        instance_uuid = response.get('response')
        output = [f"Deployed instance with UUID: {instance_uuid}"]

        if ssh_key_list:
          output.append("Added SSH keys:")
          for key in ssh_key_list:
            output.append(f"  - {key}")

        result = "\n".join(output)

        return result

      except requests.exceptions.HTTPError as e:
        if e.response is not None:
          error_data = e.response.json()
          if 'response' in error_data:
            error_resp = error_data['response']
            if error_resp.get('code') == 'global/invalid_parameter' and 'capacity' in error_resp.get('message', '').lower():
              output = [
                f"\nError: Not enough capacity for {product_name}",
                "\nAvailable alternatives:",
                "-" * 102,
                f"{'Product':<15} {'Description':<25} {'VRAM':<10} {'Price/Hr':<10} {'GB/$Hr':<10} {'Available':<10}",
                "-" * 102
              ]

              # Show available alternatives
              for info in inventory.values():
                instance_type = info.get('instance_type', {})
                capacity = info.get('capacity_available', 0)
                if capacity > 0:  # Only show products with capacity
                  name = instance_type.get('name', 'N/A')
                  desc = instance_type.get('description', 'N/A')
                  price = instance_type.get('price_cents_per_hour', 0) / 100

                  # Calculate VRAM and GB/$ per hour if possible
                  vram = "N/A"
                  gb_per_dollar = "N/A"
                  for gpu_type, vram_amount in GPU_VRAM.items():
                    if gpu_type.lower() in name.lower():
                      multiplier = 1
                      if "gpu_" in name.lower() and "x_" in name.lower():
                        try:
                          multiplier = int(name.split("x_")[0].split("gpu_")[1])
                        except ValueError:
                          pass
                      total_vram = vram_amount * multiplier
                      vram = f"{total_vram}GB"
                      if price > 0:
                        gb_per_dollar = f"{total_vram/price:.1f}"
                      break

                  output.append(f"{name[:15]:<15} {desc[:25]:<25} {vram:<10} ${price:<9.2f} {gb_per_dollar:<10} {capacity:<10}")

              print("\n".join(output))
              return "\n".join(output)

        # If we couldn't parse the error or it's a different error, show the original message
        error_msg = f"Error deploying instance: {str(e)}"
        print(error_msg)
        return error_msg

    except Exception as e:
      error_msg = f"Error: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["terminate"],
    description="Terminate one or more instances by UUID or name",
    help_text="Terminate one or more instances by UUID or name",
    parameters={
      "type": "object",
      "properties": {
        "identifiers": {
          "type": "string",
          "description": "Space-separated list of instance UUIDs or names to terminate"
        }
      },
      "required": ["identifiers"]
    }
  )
  def terminate_instances(self, settings: Settings, identifiers: str) -> str:
    """Terminate one or more instances by UUID or name"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    if not identifiers:
      msg = "Error: Must specify at least one instance UUID or name to terminate"
      print(msg)
      return msg

    # Split the identifiers into a list
    args = identifiers.split()

    try:
      api = MassedComputeAPI(settings)
      instances = api.get_instances()
      uuids_to_terminate = []

      # Process each argument (UUID or name)
      for identifier in args:
        # Check if it matches any instance names
        matching_instances = [i for i in instances if i.get('name') == identifier]

        if matching_instances:
          if len(matching_instances) > 1:
            print(f"\nWarning: Multiple instances found with name '{identifier}':")
            for inst in matching_instances:
              print(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
            print("Please use UUID to terminate specific instance")
            continue
          else:
            instance_uuid = matching_instances[0].get('uuid')
            instance_name = matching_instances[0].get('name')
            print(f"Found instance '{instance_name}' with UUID: {instance_uuid}")
            uuids_to_terminate.append(instance_uuid)
        else:
          # Assume it's a UUID
          uuids_to_terminate.append(identifier)

      if not uuids_to_terminate:
        msg = "No valid instances found to terminate"
        print(msg)
        return msg

      # Confirm termination
      output = ["\nPreparing to terminate the following instances:"]
      for uuid in uuids_to_terminate:
        matching = next((i for i in instances if i.get('uuid') == uuid), None)
        if matching:
          output.append(f"  {matching.get('name')} ({uuid})")
        else:
          output.append(f"  {uuid}")

      confirm = input("\nAre you sure you want to terminate these instances? (y/N): ")
      if confirm.lower() != 'y':
        msg = "Termination cancelled"
        print(msg)
        return msg

      # Proceed with termination
      response = api.terminate_instances(uuids_to_terminate)

      # Print results
      terminated = response.get('response', {}).get('data', {}).get('terminated_instances', [])
      if terminated:
        output.append("\nSuccessfully terminated instances:")
        for instance in terminated:
          name = instance.get('name', 'N/A')
          uuid = instance.get('id', 'N/A')
          output.append(f"  {name} ({uuid})")
      else:
        output.append("No instances were terminated")

      result = "\n".join(output)

      return result

    except Exception as e:
      error_msg = f"Error terminating instances: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["details"],
    description="Get detailed information about a specific instance",
    help_text="Get detailed information about a specific instance by UUID or name",
    parameters={
      "type": "object",
      "properties": {
        "identifier": {
          "type": "string",
          "description": "UUID or name of the instance to get details for"
        }
      },
      "required": ["identifier"]
    }
  )
  def get_instance_details(self, settings: Settings, identifier: str) -> str:
    """Get detailed information about a specific instance"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)

      # First try to get instance directly if UUID was provided
      instance = None
      try:
        instance = api.get_instance_details(identifier)
      except:
        # If that fails, try to find instance by name
        instances = api.get_instances()
        matching_instances = [i for i in instances if i.get('name') == identifier]

        if len(matching_instances) > 1:
          output = [f"\nMultiple instances found with name '{identifier}':"]
          for inst in matching_instances:
            output.append(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
          output.append("Please use UUID to get details of specific instance")
          print("\n".join(output))
          return "\n".join(output)
        elif len(matching_instances) == 1:
          instance = matching_instances[0]

      if not instance:
        msg = f"No instance found with identifier: {identifier}"
        print(msg)
        return msg

      # Print basic info
      output = [
        "\nInstance Details:",
        "-" * 72,
        f"Name: {instance.get('name', 'N/A')}",
        f"UUID: {instance.get('uuid', 'N/A')}",
        f"Status: {instance.get('status', 'N/A')}",
        f"IP Address: {instance.get('ip', 'N/A')}",
        f"Username: {instance.get('username', 'N/A')}",
        f"Password: {instance.get('password', 'N/A')}",
        f"Created: {instance.get('created', 'N/A')}"
      ]

      # Print startup command if present
      startup_cmd = instance.get('command_startup')
      if startup_cmd:
        output.append(f"Startup Command: {startup_cmd}")

      # Print image info
      image = instance.get('image', {})
      output.extend([
        "\nImage:",
        f"  ID: {image.get('id', 'N/A')}",
        f"  Name: {image.get('name', 'N/A')}",
        f"  Description: {image.get('description', 'N/A')}"
      ])

      # Print product info
      product = instance.get('product', {})
      output.extend([
        "\nProduct:",
        f"  Name: {product.get('name', 'N/A')}",
        f"  Description: {product.get('description', 'N/A')}",
        f"  GPU Count: {product.get('gpu_count', 'N/A')}",
        f"  vCPUs: {product.get('vcpu', 'N/A')}",
        f"  RAM: {product.get('ram', 'N/A')} GB",
        f"  Storage: {product.get('storage', 'N/A')} GB",
        f"  Price/Hour: ${float(product.get('price_hr', 0)):.2f}"
      ])

      result = "\n".join(output)
      print(result)
      return result

    except Exception as e:
      error_msg = f"Error getting instance details: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["ssh"],
    description="Connect to instance via SSH",
    help_text="Connect to instance via SSH using UUID or instance name",
    parameters={
      "type": "object",
      "properties": {
        "identifier": {
          "type": "string",
          "description": "UUID or name of the instance to connect to"
        }
      },
      "required": ["identifier"]
    }
  )
  def ssh_to_instance(self, settings: Settings, identifier: str) -> str:
    """Connect to instance via SSH"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)

      # First try to get instance directly if UUID was provided
      instance = None
      try:
        instance = api.get_instance_details(identifier)
      except:
        # If that fails, try to find instance by name
        instances = api.get_instances()
        matching_instances = [i for i in instances if i.get('name') == identifier]

        if len(matching_instances) > 1:
          output = [f"Multiple instances found with name '{identifier}':"]
          for inst in matching_instances:
            output.append(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
          output.append("Please use UUID to connect to specific instance")
          print("\n".join(output))
          return "\n".join(output)
        elif len(matching_instances) == 1:
          instance = matching_instances[0]

      if not instance:
        msg = f"No instance found with identifier: {identifier}"
        print(msg)
        return msg

      ip = instance.get('ip')
      username = instance.get('username')
      password = instance.get('password')
      name = instance.get('name')

      if not all([ip, username, password]):
        msg = "Error: Missing connection details for instance"
        print(msg)
        return msg

      print(f"\nConnecting to {name} ({username}@{ip})...")

      # Construct sshpass command based on platform
      if platform.system() == "Windows":
        output = [
          "Connection details:",
          f"  Host: {ip}",
          f"  Username: {username}",
          f"  Password: {password}",
          "\nPlease use these credentials in your SSH client"
        ]
        print("\n".join(output))
        return "\n".join(output)

      # For Unix-like systems, use sshpass
      ssh_command = [
        "sshpass",
        "-p",
        password,
        "ssh",
        "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{username}@{ip}"
      ]

      try:
        subprocess.run(ssh_command)
        return "SSH session ended"
      except FileNotFoundError:
        output = [
          "Error: 'sshpass' is required but not installed.",
          "Install it with:"
        ]
        if platform.system() == "Darwin":  # macOS
          output.append("  brew install hudochenkov/sshpass/sshpass")
        else:  # Linux
          output.extend([
            "  sudo apt-get install sshpass  # Ubuntu/Debian",
            "  sudo yum install sshpass      # CentOS/RHEL"
          ])
        print("\n".join(output))
        return "\n".join(output)

    except Exception as e:
      error_msg = f"Error connecting to instance: {str(e)}"
      print(error_msg)
      return error_msg

  @command(
    path=["run"],
    description="Run a predefined script on an instance",
    help_text="Run a predefined script on an instance using SSH",
    parameters={
      "type": "object",
      "properties": {
        "identifier": {
          "type": "string",
          "description": "UUID or name of the instance to run the script on"
        },
        "script_name": {
          "type": "string",
          "description": "Name of the script to run ('vllm', 'test', etc.)"
        }
      },
      "required": ["identifier", "script_name"]
    }
  )
  def run_script(self, settings: Settings, identifier: str, script_name: str) -> str:
    """Run a predefined script on an instance"""
    if not settings.massed_compute_api_token:
      msg = "MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment."
      print(msg)
      return msg

    try:
      api = MassedComputeAPI(settings)

      # Get instance details
      instance = None
      try:
        instance = api.get_instance_details(identifier)
      except:
        instances = api.get_instances()
        matching_instances = [i for i in instances if i.get('name') == identifier]

        if len(matching_instances) > 1:
          output = [f"\nMultiple instances found with name '{identifier}':"]
          for inst in matching_instances:
            output.append(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
          output.append("Please use UUID to run script on specific instance")
          print("\n".join(output))
          return "\n".join(output)
        elif len(matching_instances) == 1:
          instance = matching_instances[0]

      if not instance:
        msg = f"No instance found with identifier: {identifier}"
        print(msg)
        return msg

      # Get script
      script = get_startup_script(script_name.lower(), settings)
      if script is None:
        msg = f"Unknown script: {script_name}\nAvailable scripts: {', '.join(STARTUP_SCRIPTS.keys())}"
        print(msg)
        return msg

      ip = instance.get('ip')
      username = instance.get('username')
      password = instance.get('password')
      name = instance.get('name')

      if not all([ip, username, password]):
        msg = "Error: Missing connection details for instance"
        print(msg)
        return msg

      print(f"\nRunning script '{script_name}' on instance '{name}'...")

      # For Windows, show manual instructions
      if platform.system() == "Windows":
        output = [
          "\nWindows detected. Please run these commands in your SSH client:",
          f"Host: {ip}",
          f"Username: {username}",
          f"Password: {password}",
          "\nCommands to run:",
          script
        ]
        print("\n".join(output))
        return "\n".join(output)

      # For Unix-like systems, use sshpass to execute the script
      ssh_command = [
        "sshpass",
        "-p",
        password,
        "ssh",
        "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{username}@{ip}",
        script
      ]

      try:
        result = subprocess.run(ssh_command, capture_output=True, text=True)
        output = []

        if result.returncode == 0:
          output.append("\nScript executed successfully")
          if result.stdout:
            output.extend(["\nOutput:", result.stdout])
        else:
          output.append("\nScript execution failed")
          if result.stderr:
            output.extend(["\nError output:", result.stderr])

        print("\n".join(output))
        return "\n".join(output)

      except FileNotFoundError:
        output = [
          "Error: 'sshpass' is required but not installed.",
          "Install it with:"
        ]
        if platform.system() == "Darwin":  # macOS
          output.append("  brew install hudochenkov/sshpass/sshpass")
        else:  # Linux
          output.extend([
            "  sudo apt-get install sshpass  # Ubuntu/Debian",
            "  sudo yum install sshpass      # CentOS/RHEL"
          ])
        print("\n".join(output))
        return "\n".join(output)

    except Exception as e:
      error_msg = f"Error running script: {str(e)}"
      print(error_msg)
      return error_msg



########################################################################
#                           HELPER FUNCTIONS                           #
########################################################################
def format_images_table(images: List[Dict[str, Any]]) -> List[str]:
  """Formats image data into printable table rows."""
  if not images:
    return ["No images available"]

  output = []

  for image in images:
    # Add ID and name on first line
    output.append(f"{image['vm_image_id']} {image['vm_image_name']}")

    # Split description by newlines first
    desc_parts = image['vm_image_description'].split('\n')

    for desc in desc_parts:
      desc = desc.strip()
      if not desc:  # Skip empty lines
        continue

      first_line = True
      # Wrap at 68 chars to account for 4 space indent (72 char limit)
      while desc:
        max_length = 68 if first_line else 66  # Account for "  " prefix on continuation
        if len(desc) <= max_length:
          prefix = "    - " if first_line else "      "
          output.append(f"{prefix}{desc}")
          break

        # Find last space before max_length
        split_idx = desc[:max_length].rstrip().rfind(' ')
        if split_idx == -1:
          split_idx = max_length

        prefix = "    - " if first_line else "      "
        output.append(f"{prefix}{desc[:split_idx]}")
        desc = desc[split_idx:].lstrip()
        first_line = False

    output.append("")  # Add blank line between images

  return output[:-1]  # Remove last blank line

def format_instances_table(instances: List[Dict[str, Any]]) -> List[str]:
  """Formats instance data into printable table rows."""
  if not instances:
    return ["No running instances"]

  output = [
    "\nRunning Instances:",
    "-" * 100,
    f"{'Name':<20} {'UUID':<40} {'Status':<10} {'IP':<15} Product",
    "-" * 100,
  ]

  for instance in instances:
    name = instance.get('name', 'N/A')[:19]
    uuid = instance.get('uuid', 'N/A')
    status = instance.get('status', 'N/A')
    ip = instance.get('ip', 'N/A')
    product = instance.get('product', {}).get('name', 'N/A')

    output.append(f"{name:<20} {uuid:<40} {status:<10} {ip:<15} {product}")

  return output

def get_startup_script(script_name: str, settings: Optional[Settings] = None, extra_params: Optional[Dict[str, str]] = None) -> Optional[str]:
  """
  Get a startup script by name, joining the commands with && if found.

  Args:
      script_name: Name of the script to retrieve
      settings: Optional Settings object for token replacement
      extra_params: Optional dictionary of additional parameters to replace

  Returns:
      Joined script commands if found, None otherwise
  """
  if script_name not in STARTUP_SCRIPTS:
    return None

  script = " && ".join(STARTUP_SCRIPTS[script_name])

  # Create parameters dictionary
  params = {}

  # Add HuggingFace token if available
  if settings and settings.huggingface_api_token:
    params['hf_token'] = settings.huggingface_api_token

  # Add VLLM-specific parameters if available
  if settings:
    if settings.vllm_zone and settings.vllm_subdomain:
      params['subdomain'] = settings.vllm_subdomain
    if settings.vllm_email:
      params['email'] = settings.vllm_email
    if settings.vllm_zone:
      params['zone'] = settings.vllm_zone
    if settings.cloudflare_api_token:
      params['cloudflare_token'] = settings.cloudflare_api_token
    if settings.vllm_eab_kid:
      params['eab_kid'] = settings.vllm_eab_kid
    if settings.vllm_eab_hmac_encoded:
      params['eab_hmac_encoded'] = settings.vllm_eab_hmac_encoded

  # Add any additional parameters
  if extra_params:
    params.update(extra_params)

  # Replace all parameters in the script
  try:
    script = script.format(**params)
  except KeyError as e:
    missing_param = str(e).strip("'")
    raise ValueError(f"Missing required parameter: {missing_param}")

  return script

def parse_extra_params(args: List[str]) -> Dict[str, str]:
  """Parse key=value parameters from argument list."""
  params = {}
  for arg in args:
    if '=' in arg:
      key, value = arg.split('=', 1)
      params[key] = value
  return params

def handle_ssh_keys(key_args: List[str]) -> List[str]:
  """Helper function to process SSH key arguments."""
  ssh_keys = []
  current_key = []
  in_quotes = False

  for arg in key_args:
    if arg.startswith('"') and arg.endswith('"'):
      # Handle key wrapped in quotes
      ssh_keys.append(arg.strip('"'))
    elif arg.startswith('"'):
      # Start of quoted key
      in_quotes = True
      current_key = [arg.strip('"')]
    elif arg.endswith('"'):
      # End of quoted key
      in_quotes = False
      current_key.append(arg.strip('"'))
      ssh_keys.append(' '.join(current_key))
      current_key = []
    elif in_quotes:
      # Middle of quoted key
      current_key.append(arg)
    else:
      # Regular unquoted key
      ssh_keys.append(arg)

  # Handle unclosed quotes
  if current_key:
    ssh_keys.append(' '.join(current_key))

  return ssh_keys



########################################################################
#                              API CLASS                               #
########################################################################
# This class is responsible for interacting with the MassedCompute API.
class MassedComputeAPI:
  def __init__(self, settings: Settings):
    """Initialize the MassedCompute API client"""
    if not settings.massed_compute_api_token:
      raise ValueError("MassedCompute API token not found.")

    self.api_token = settings.massed_compute_api_token
    self.base_url = "https://vm.massedcompute.com/api/v1"
    self.headers = {
      "Authorization": f"Bearer {self.api_token}",
      "Content-Type": "application/json"
    }

  def get_images(self) -> List[Dict[str, Any]]:
    """Get list of available images from API."""
    response = requests.get(
      f"{self.base_url}/images",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('images', [])

  def get_instances(self) -> List[Dict[str, Any]]:
    """Get list of running instances from API."""
    response = requests.get(
      f"{self.base_url}/instance",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('runningInstances', [])

  def deploy_cheapest_instance(
    self,
    image_id: int,
    instance_name: Optional[str] = None,
    startup_script: Optional[str] = None,
    ssh_keys: Optional[List[str]] = None
  ) -> Dict[str, Any]:
    """
    Deploy the cheapest available GPU instance.

    Args:
        image_id: The ID of the image to deploy
        instance_name: Optional name for the instance
        startup_script: Optional startup script to run on instance launch
        ssh_keys: Optional list of SSH key names to add to the instance

    Returns:
        Dict containing the deployment response with instance UUID
    """
    # Get GPU inventory to find cheapest option
    inventory = self.get_gpu_inventory()

    # Find cheapest GPU with available capacity
    cheapest_price = float('inf')
    cheapest_product = None

    for product_info in inventory.values():
      price = product_info.get('instance_type', {}).get('price_cents_per_hour', float('inf'))
      capacity = product_info.get('capacity_available', 0)

      if capacity > 0 and price < cheapest_price:
        cheapest_price = price
        cheapest_product = product_info['instance_type']['name']

    if not cheapest_product:
      raise ValueError("No GPU instances currently available")

    # Deploy the instance
    deploy_data = {
      "imageId": image_id,
      "productName": cheapest_product,
      "regionName": "any"
    }

    if instance_name:
      deploy_data["instanceName"] = instance_name

    if startup_script:
      deploy_data["command"] = startup_script

    if ssh_keys:
      deploy_data["sshKey"] = ssh_keys

    deploy_response = requests.post(
      f"{self.base_url}/instance/launch",
      headers=self.headers,
      json=deploy_data
    )
    deploy_response.raise_for_status()

    return deploy_response.json()

  def get_gpu_inventory(self) -> Dict[str, Any]:
    """Get GPU inventory information from API."""
    response = requests.get(
      f"{self.base_url}/gpu-inventory",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('gpu_inventory', {})

  def terminate_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
    """
    Terminate one or more instances.

    Args:
        instance_uuids: List of instance UUIDs to terminate

    Returns:
        API response containing termination results
    """
    response = requests.post(
      f"{self.base_url}/instance/terminate",
      headers=self.headers,
      json={"instanceUuids": instance_uuids}
    )
    response.raise_for_status()
    return response.json()

  def get_instance_details(self, instance_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific instance.

    Args:
        instance_uuid: UUID of the instance to query

    Returns:
        Dict containing instance details if found, None otherwise
    """
    response = requests.get(
      f"{self.base_url}/instance/{instance_uuid}",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('runningInstances')[0]

  def deploy_specific_instance(
    self,
    image_id: int,
    product_name: str,
    instance_name: Optional[str] = None,
    startup_script: Optional[str] = None,
    ssh_keys: Optional[List[str]] = None
  ) -> Dict[str, Any]:
    """
    Deploy a specific GPU instance type.

    Args:
        image_id: The ID of the image to deploy
        product_name: The specific product name to deploy
        instance_name: Optional name for the instance
        startup_script: Optional startup script to run on instance launch
        ssh_keys: Optional list of SSH key names to add to the instance

    Returns:
        Dict containing the deployment response with instance UUID
    """
    deploy_data = {
      "imageId": image_id,
      "productName": product_name,
      "regionName": "any"
    }

    if instance_name:
      deploy_data["instanceName"] = instance_name

    if startup_script:
      deploy_data["command"] = startup_script

    if ssh_keys:
      deploy_data["sshKey"] = ssh_keys

    deploy_response = requests.post(
      f"{self.base_url}/instance/launch",
      headers=self.headers,
      json=deploy_data
    )
    deploy_response.raise_for_status()

    return deploy_response.json()
