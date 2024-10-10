## notes

### debug with curl

```
For windows cmd.exe:
curl -X PUT "localhost:32323/api/v1/telescope/0/commandstring" ^
     -H "accept: application/json" ^
     -H "Content-Type: application/x-www-form-urlencoded" ^
     -d "ClientID=111&ClientTransactionID=222&Command=XXam&Raw=True"

returns-> {"ClientTransactionID":222,"ServerTransactionID":8,"ErrorNumber":1024,"ErrorMessage":"Method CommandString is not implemented in this driver."}

for linux:
 curl -X PUT "192.168.6.214:32323/api/v1/telescope/0/commandstring" \
     -H "accept: application/json" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "ClientID=111&ClientTransactionID=222&Command=XXam&Raw=True"

curl -X GET "192.168.6.214:32323/api/v1/telescope/0/declination" \
     -H "accept: application/json"

returns-> {"Value":-13.07861,"ClientTransactionID":0,"ServerTransactionID":7,"ErrorNumber":0,"ErrorMessage":""}
```
### bitness
Is this a cause of problems?
`python -c "import platform; print(platform.architecture())"`
