from Encrypt import AESCipher

class A:
    def __init__(self,name):
        self.name = name

first = A("Chaitanya")
Encryption_object = AESCipher("password")

Encrypted_object = Encryption_object.encrypt("Chaitanya")
print Encrypted_object
print Encryption_object.decrypt(Encrypted_object)
