import logging
import time
import grpc
from cryptography.hazmat.primitives import serialization

from spiffe import WorkloadApiClient

import agent_pb2
import agent_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run():
    logging.info("Starting Agent A (Zero Trust Client)...")
    
    for i in range(10):
        try:
            with WorkloadApiClient() as client:
                svid = client.fetch_x509_svid()
                logging.info(f"Successfully fetched identity: {svid.spiffe_id}")
                break
        except Exception as e:
            logging.warning(f"Waiting for SPIRE Agent... ({e})")
            time.sleep(2)
    else:
        logging.error("Could not connect to SPIRE after 10 retries.")
        return

    with WorkloadApiClient() as client:
        svid = client.fetch_x509_svid()
        logging.info(f"Successfully fetched identity from SPIRE: {svid.spiffe_id}")
        
        private_key_pem = svid.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        cert_chain_pem = b"".join(
            cert.public_bytes(serialization.Encoding.PEM) for cert in svid.cert_chain
        )
        
        bundles = client.fetch_x509_bundles()
        root_certificates_pem = b""
        
        for bundle in bundles.bundles:
            for cert in bundle.x509_authorities:
                root_certificates_pem += cert.public_bytes(serialization.Encoding.PEM)

    credentials = grpc.ssl_channel_credentials(
        root_certificates=root_certificates_pem,
        private_key=private_key_pem,
        certificate_chain=cert_chain_pem
    )

    
    # target_spiffe_id = "spiffe://blog.local/agent_b"
    
    # options = (
    #     ('grpc.ssl_target_name_override', target_spiffe_id),
    # )

    # logging.info("Connecting to Agent B via mTLS...")
    # with grpc.secure_channel('agent-b-server:50051', credentials) as channel:
    #     stub = agent_pb2_grpc.AgentCommunicationStub(channel)


    logging.info("Connecting to Agent B via mTLS...")
    with grpc.secure_channel('agent-b-server:50051', credentials) as channel:
        stub = agent_pb2_grpc.AgentCommunicationStub(channel)
        while True:
            try:
                logging.info("Sending prompt to Agent B...")
                request = agent_pb2.MessageRequest(prompt_text="Hello Agent B, do you trust me?")
                response = stub.SendPrompt(request, timeout=5)
                logging.info(f"Response from Agent B: {response.response_text}")
            except grpc.RpcError as e:
                logging.error(f"RPC failed: {e.code()} - {e.details()}")
            
            time.sleep(5)

if __name__ == '__main__':
    run()
