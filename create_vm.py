from google.cloud import compute_v1

def create_instance_with_public_ip(
    project_id: str,
    zone: str,
    instance_name: str,
    machine_type: str,
    image_family: str,
    image_project: str,
    disk_size_gb: int,
    disk_type: str,
    tags: list,
    startup_script_path: str
) -> str:
    """
    Creates a Google Cloud VM instance with the specified parameters.

    Args:
        project_id (str): Google Cloud project ID.
        zone (str): Zone to create the instance in.
        instance_name (str): Name of the VM instance.
        machine_type (str): Machine type for the VM (e.g., e2-standard-8).
        image_family (str): Image family for the boot disk.
        image_project (str): Project hosting the image family.
        disk_size_gb (int): Size of the boot disk in GB.
        disk_type (str): Disk type (e.g., pd-ssd).
        tags (list): List of network tags.
        startup_script_path (str): Path to the startup script file.

    Returns:
        str: External IP address of the created instance.
    """
    instance_client = compute_v1.InstancesClient()
    image_client = compute_v1.ImagesClient()

    # Get the latest image from the specified family
    image_response = image_client.get_from_family(project=image_project, family=image_family)
    source_disk_image = image_response.self_link

    # Configure the boot disk
    disk = compute_v1.AttachedDisk()
    disk.auto_delete = True
    disk.boot = True
    disk.initialize_params = compute_v1.AttachedDiskInitializeParams(
        source_image=source_disk_image,
        disk_size_gb=disk_size_gb,
        disk_type=f"zones/{zone}/diskTypes/{disk_type}",
    )

    # Configure the machine type
    machine_type_full = f"zones/{zone}/machineTypes/{machine_type}"

    # Load the startup script
    with open(startup_script_path, "r") as script_file:
        startup_script = script_file.read()

    # Configure metadata for the instance
    metadata = compute_v1.Metadata()
    metadata.items = [{"key": "startup-script", "value": startup_script}]

    # Configure network tags
    tags_obj = compute_v1.Tags()
    tags_obj.items = tags

    # Configure the network interface with a public IP
    network_interface = compute_v1.NetworkInterface()
    network_interface.name = "default"
    access_config = compute_v1.AccessConfig(
        name="External NAT",
        type_="ONE_TO_ONE_NAT"  # Enable public IP
    )
    network_interface.access_configs = [access_config]

    # Define the instance
    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.disks = [disk]
    instance.machine_type = machine_type_full
    instance.metadata = metadata
    instance.network_interfaces = [network_interface]
    instance.tags = tags_obj

    # Create the instance
    operation = instance_client.insert(
        project=project_id,
        zone=zone,
        instance_resource=instance,
    )
    print(f"Instance creation started: {operation}")

    # Wait for the operation to complete
    operation_client = compute_v1.ZoneOperationsClient()
    operation_result = operation_client.wait(
        operation=operation.name, project=project_id, zone=zone
    )
    print(f"Instance creation finished: {operation_result}")

    # Retrieve the external IP address of the instance
    instance_info = instance_client.get(project=project_id, zone=zone, instance=instance_name)
    external_ip = None
    for iface in instance_info.network_interfaces:
        if iface.access_configs:
            external_ip = iface.access_configs[0].nat_i_p  # Correct field name
            break

    if external_ip:
        print(f"External IP: {external_ip}")
        return external_ip
    else:
        raise RuntimeError("Failed to retrieve external IP address for the instance.")
