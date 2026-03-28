import logging
from concurrent import futures
import grpc
import time
from cryptography.hazmat.primitives import serialization

from spiffe import WorkloadApiClient

import agent_pb2
import agent_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AgentCommunicationServicer(agent_pb2_grpc.AgentCommunicationServicer):
    def SendPrompt(self, request, context):
        identities = context.peer_identities()
        if identities:
            peer_identity = identities[0].decode('utf-8')
        else:
            peer_identity = "Unknown"
        logging.info(f"Authenticated mTLS request received from: {peer_identity}")
        logging.info(f"Prompt content: {request.prompt_text}")
        
        response_msg = f"Hello {peer_identity}, your message '{request.prompt_text}' was successfully received and validated."
        return agent_pb2.MessageReply(response_text=response_msg)

def serve():
    logging.info("Starting Agent B (Zero Trust Server)...")
    
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
  
    
    credentials = grpc.ssl_server_credentials(
        [(private_key_pem, cert_chain_pem)],
        root_certificates=root_certificates_pem,
        require_client_auth=True
    )
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    agent_pb2_grpc.add_AgentCommunicationServicer_to_server(AgentCommunicationServicer(), server)
    
    server.add_secure_port('[::]:50051', credentials)
    server.start()
    
    logging.info("Agent B is listening on port 50051 with strict mTLS (SPIFFE).")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()