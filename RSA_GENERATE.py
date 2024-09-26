import rsa

# Gera um par de chaves RSA
(public_key,private_key) = rsa.newkeys(2048)

# Salva a chave privada em um arquivo PEM
with open("private_key.pem", "wb") as private_key_file:
    private_key_pem = private_key.save_pkcs1(format='PEM')
    private_key_file.write(private_key_pem)

# Salva a chave pública em um arquivo PEM
with open("public_key.pem", "wb") as public_key_file:
    public_key_pem = public_key.save_pkcs1(format='PEM')
    public_key_file.write(public_key_pem)
