import logging
from hashlib import sha256

# from nacl.signing import SigningKey

log = logging.getLogger(__name__)


def compute_sha256(filepath):
    buf_size = 65536
    bin_sha256 = sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            bin_sha256.update(data)
    return bin_sha256.hexdigest()


# def compute_signature(filepath):
# try:
#     skey = env["SKEY"]
# except KeyError:
#     log.error("SKEY needs to be set as env variable")
#     raise KeyError
# with open(filepath, "rb") as f:
#        byte_file = f.read()
#        skey = SigningKey.generate()
#        signed = skey.sign(byte_file)
#     signature = skey.verify_key
#     signature_bytes = signature.encode()
# return signature_bytes
