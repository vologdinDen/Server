# Http-service
The service has three handles that handle POST, GET and DELETE http-requests. 
- In the body of the POST request it is necessary to pass JSON in which it is necessary to pass the url of the downloaded archive. The handle will return the archive ID in the service. 
- When making a GET request, you must specify the archive ID in the service, then the handle will return its state: downloaded, unpacked or already unpacked
- When you delete a request, you must specify the archive ID in the service, then the handle will delete the archive and the unpacked files

Request examples:
- curl -X POST http://127.0.0.1:8080/archive -d '{"url":"path_to_archive"}'
- curl -X GET http://127.0.0.1:8080/archive/{id}
- curl -X DELETE http://127.0.0.1:8080/archive/{id}