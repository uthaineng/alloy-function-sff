import oci
import json
import os
import io
import logging
from fdk import response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def handler(ctx, data: io.BytesIO = None):
    vmcluster_ocid = os.environ.get("VMCLUSTER_OCID", "not-set")
    ecpu_count_str = os.environ.get("ECPU_COUNT")

    if not ecpu_count_str:
        ecpu_count_str = "16"

    logger.info("Function handler triggered.")
    logger.info(f"Target VM Cluster: {vmcluster_ocid}, Desired ECPU: {ecpu_count_str}")

    try:
        target_ocpu = int(ecpu_count_str)
    except ValueError:
        logger.error(f"Invalid ECPU value: {ecpu_count_str}. Must be an integer.")
        return response.Response(
            ctx,
            response_data=json.dumps({"error": "Invalid ECPU value"}),
            status_code=400,
            headers={"Content-Type": "application/json"}
        )

    try:
        scale_exacs(vmcluster_ocid, target_ocpu)
        return response.Response(
            ctx,
            response_data=json.dumps({"result": "Scale request submitted"}),
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        return response.Response(
            ctx,
            response_data=json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

def scale_exacs(cluster_ocid, target_ocpu):
    logger.info("Starting async scale_exacs process...")
    signer = oci.auth.signers.get_resource_principals_signer()
    database_client = oci.database.DatabaseClient(config={}, signer=signer)

    try:
        response_vm = database_client.get_cloud_vm_cluster(
            cloud_vm_cluster_id=cluster_ocid
        )
        current_cpu = response_vm.data.cpu_core_count
        logger.info(f"Current CPU core count: {current_cpu}")

        if current_cpu == target_ocpu:
            logger.info("Target ECPU is equal to current CPU. No scaling needed.")
            return

        database_client.update_cloud_vm_cluster(
            cloud_vm_cluster_id=cluster_ocid,
            update_cloud_vm_cluster_details=oci.database.models.UpdateCloudVmClusterDetails(
                cpu_core_count=target_ocpu
            )
        )
        logger.info(f"Scale request submitted to set ECPU = {target_ocpu}")

    except oci.exceptions.ServiceError as e:
        logger.error(f"OCI ServiceError: {e.message} - {e.code} - {e.status} - {e.request_id}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during scale_exacs: {str(e)}")
        raise
