# Dev RS256 klíče

SmallRye JWT podepisuje RS256. Vygeneruj dev pár (jen DEV klíče smí do repa):

```bash
openssl genrsa -out rsaPrivate.pem 2048
openssl pkcs8 -topk8 -inform PEM -in rsaPrivate.pem -out privateKey.pem -nocrypt
openssl rsa -in rsaPrivate.pem -pubout -out publicKey.pem
rm rsaPrivate.pem
```

Výstup: `privateKey.pem` + `publicKey.pem` v tomto adresáři. Produkční klíče
se NIKDY necommitují — injektují se přes `JWT_KEY_DIR` (viz `application.properties`).
