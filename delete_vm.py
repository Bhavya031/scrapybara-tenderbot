from google.cloud import compute_v1

def delete_instance(
    project_id: str,
    zone: str,
    instance_name: str
) -> None:
    """
    Deletes a Google Cloud VM instance.

    Args:
        project_id (str): Google Cloud project ID.
        zone (str): Zone of the instance to delete.
        instance_name (str): Name of the VM instance to delete.

    Returns:
        None
    """
    instance_client = compute_v1.InstancesClient()

    print(f"Deleting instance '{instance_name}' in zone '{zone}'...")
    operation = instance_client.delete(
        project=project_id,
        zone=zone,
        instance=instance_name
    )

    # Wait for the operation to complete
    operation_client = compute_v1.ZoneOperationsClient()
    operation_result = operation_client.wait(
        operation=operation.name,
        project=project_id,
        zone=zone
    )
    print(f"Instance '{instance_name}' deleted successfully: {operation_result}")
