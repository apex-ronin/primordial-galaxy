#!/usr/bin/env python3
"""
Oracle Cloud Always-Free A1 Instance Hunter
Attempts to provision a VM.Standard.A1.Flex instance (4 OCPU, 24 GB RAM, 200 GB storage).

Designed to run inside GitHub Actions on a schedule. Reads all config from
environment variables (set as GitHub Secrets). Exits 0 on success, 1 if all
ADs are at capacity (normal / retry next run), 2 on a real error.
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    import oci
except ImportError:
    print("ERROR: oci package not installed. Run: pip install oci")
    sys.exit(2)

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
TENANCY_OCID    = os.environ["OCI_TENANCY_OCID"]
USER_OCID       = os.environ["OCI_USER_OCID"]
FINGERPRINT     = os.environ["OCI_FINGERPRINT"]
PRIVATE_KEY     = os.environ["OCI_PRIVATE_KEY"]      # Full PEM key contents
REGION          = os.environ.get("OCI_REGION", "us-ashburn-1")
COMPARTMENT_ID  = os.environ.get("OCI_COMPARTMENT_OCID", TENANCY_OCID)
SSH_PUBLIC_KEY  = os.environ["OCI_SSH_PUBLIC_KEY"]
INSTANCE_NAME   = os.environ.get("OCI_INSTANCE_NAME", "primordial-galaxy")

# OCI SDK config — key_content avoids writing a temp file
OCI_CONFIG = {
    "tenancy":     TENANCY_OCID,
    "user":        USER_OCID,
    "fingerprint": FINGERPRINT,
    "key_content": PRIVATE_KEY,
    "region":      REGION,
}


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def get_availability_domains(identity: oci.identity.IdentityClient) -> list[str]:
    ads = identity.list_availability_domains(compartment_id=TENANCY_OCID)
    return [ad.name for ad in ads.data]


def get_arm_image_id(compute: oci.core.ComputeClient) -> str:
    """Return the OCID of the latest Ubuntu 22.04 ARM64 image, fall back to Oracle Linux 8."""
    for os_name, os_ver in [("Canonical Ubuntu", "22.04"), ("Oracle Linux", "8")]:
        imgs = compute.list_images(
            compartment_id=COMPARTMENT_ID,
            operating_system=os_name,
            operating_system_version=os_ver,
            shape="VM.Standard.A1.Flex",
            sort_by="TIMECREATED",
            sort_order="DESC",
            limit=1,
        )
        if imgs.data:
            log(f"Image: {os_name} {os_ver} → {imgs.data[0].id}")
            return imgs.data[0].id
    raise RuntimeError("No ARM-compatible image found in this region.")


def get_subnet_id(network: oci.core.VirtualNetworkClient) -> str:
    """Return the OCID of the first available subnet across all VCNs."""
    vcns = network.list_vcns(compartment_id=COMPARTMENT_ID)
    if not vcns.data:
        raise RuntimeError(
            "No VCN found. Create a VCN with a public subnet in the OCI console first.\n"
            "Networking → Virtual Cloud Networks → Start VCN Wizard"
        )
    for vcn in vcns.data:
        subnets = network.list_subnets(compartment_id=COMPARTMENT_ID, vcn_id=vcn.id)
        if subnets.data:
            log(f"Subnet: {subnets.data[0].id} (VCN: {vcn.display_name})")
            return subnets.data[0].id
    raise RuntimeError("VCN exists but no subnets found. Add a public subnet.")


def try_launch(
    compute: oci.core.ComputeClient,
    ad: str,
    image_id: str,
    subnet_id: str,
) -> oci.core.models.Instance | None:
    """
    Attempt to launch the A1 instance in one availability domain.
    Returns the Instance object on success, None if the AD is out of capacity.
    Raises for any other error.
    """
    try:
        resp = compute.launch_instance(
            launch_instance_details=oci.core.models.LaunchInstanceDetails(
                compartment_id=COMPARTMENT_ID,
                availability_domain=ad,
                display_name=INSTANCE_NAME,
                shape="VM.Standard.A1.Flex",
                shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=4,
                    memory_in_gbs=24,
                ),
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image_id,
                    boot_volume_size_in_gbs=200,
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet_id,
                    assign_public_ip=True,
                ),
                metadata={"ssh_authorized_keys": SSH_PUBLIC_KEY},
                freeform_tags={
                    "project": "primordial-galaxy",
                    "provisioned_by": "oracle-hunter",
                },
            )
        )
        return resp.data
    except oci.exceptions.ServiceError as e:
        capacity_msgs = ("Out of host capacity", "InternalError", "out of capacity")
        if any(m in str(e.message) for m in capacity_msgs) or e.status in (500, 429):
            return None
        raise


def main() -> None:
    log("Oracle A1 Hunter — run starting")

    # Safe format check — shows first 20 chars only, never exposes full values
    log(f"  tenancy    : {TENANCY_OCID[:20]}...")
    log(f"  user       : {USER_OCID[:20]}...")
    log(f"  fingerprint: {FINGERPRINT[:20]}...")
    log(f"  region     : {REGION}")
    log(f"  key present: {bool(PRIVATE_KEY and len(PRIVATE_KEY) > 100)}")

    oci.config.validate_config(OCI_CONFIG)
    compute  = oci.core.ComputeClient(OCI_CONFIG)
    identity = oci.identity.IdentityClient(OCI_CONFIG)
    network  = oci.core.VirtualNetworkClient(OCI_CONFIG)

    ads      = get_availability_domains(identity)
    log(f"Availability domains: {ads}")

    image_id  = get_arm_image_id(compute)
    subnet_id = get_subnet_id(network)

    for ad in ads:
        log(f"Trying {ad} ...")
        instance = try_launch(compute, ad, image_id, subnet_id)

        if instance is None:
            log(f"  {ad}: out of capacity")
            continue

        # ----------------------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------------------
        result = {
            "id":                  instance.id,
            "display_name":        instance.display_name,
            "availability_domain": instance.availability_domain,
            "region":              REGION,
            "lifecycle_state":     instance.lifecycle_state,
            "time_created":        str(instance.time_created),
            "shape":               instance.shape,
            "ocpus":               4,
            "memory_gb":           24,
        }

        log(f"\n✅  INSTANCE CAPTURED!\n{json.dumps(result, indent=2)}")

        with open("oracle_instance.json", "w") as f:
            json.dump(result, f, indent=2)

        log("Result written to oracle_instance.json — workflow will open a GitHub issue.")
        sys.exit(0)

    log("All ADs at capacity — will retry next scheduled run.")
    sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nFATAL: {exc}", flush=True)
        sys.exit(2)
