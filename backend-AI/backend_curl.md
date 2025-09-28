C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/auth/register ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"username\":\"alice123\", \"password\":\"plain_password\", \"full_name\":\"Alice Zhang\", \"email\":\"alice@example.com\", \"phone_number\":\"13800001234\", \"security_question1\":\"你母亲的名字？\", \"security_answer1\":\"answer1\", \"security_question2\":\"你小学的名字？\", \"security_answer2\":\"answer2\" }"
{"message":"\u6ce8\u518c\u6210\u529f","success":true,"user_id":1}

C:\Users\19638>
C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/auth/login ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"username\":\"alice123\", \"password\":\"plain_password\" }"
{"expire_at":"2025-09-28T01:23:40.098104Z","success":true,"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJxaW5pdS1wcm9qZWN0Iiwic3ViIjoiMSIsImV4cCI6MTc1OTAyMjYyMCwiaWF0IjoxNzU5MDE1NDIwLCJ0eXBlIjoiYWNjZXNzIn0.aYv6GHswMxz21Jm_TdS34-ULNFqX0D2nIRlE_5T4Fws","user_id":1}

C:\Users\19638>set TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJxaW5pdS1wcm9qZWN0Iiwic3ViIjoiMSIsImV4cCI6MTc1OTAyMjYyMCwiaWF0IjoxNzU5MDE1NDIwLCJ0eXBlIjoiYWNjZXNzIn0.aYv6GHswMxz21Jm_TdS34-ULNFqX0D2nIRlE_5T4Fws

C:\Users\19638>curl -X GET http://127.0.0.1:7210/api/auth/me ^
More?  -H "Authorization: Bearer %TOKEN%"
{"created_at":"2025-09-28T07:23:31Z","email":"alice@example.com","full_name":"Alice Zhang","phone_number":"13800001234","updated_at":"2025-09-28T07:23:31Z","user_id":1,"username":"alice123"}

C:\Users\19638>curl -X PUT http://127.0.0.1:7210/api/users/1001 ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"full_name\":\"Alice Z.\", \"email\":\"alice_new@example.com\", \"phone_number\":\"13800009999\" }"
{"message":"\u65e0\u6743\u9650\u4fee\u6539\u5176\u4ed6\u7528\u6237","success":false}

C:\Users\19638>curl -X PUT http://127.0.0.1:7210/api/users/1001 ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"full_name\":\"Alice Z.\", \"email\":\"alice_new@example.com\", \"phone_number\":\"13800009999\" }"
{"message":"\u65e0\u6743\u9650\u4fee\u6539\u5176\u4ed6\u7528\u6237","success":false}

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/auth/verify-security ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"username\":\"alice123\", \"security_answer1\":\"answer1\", \"security_answer2\":\"answer2\" }"
{"reset_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJxaW5pdS1wcm9qZWN0Iiwic3ViIjoiMSIsImV4cCI6MTc1OTAxNjQyMSwiaWF0IjoxNzU5MDE1NTIxLCJ0eXBlIjoicmVzZXQifQ.WY1vbtrNii0C_3gE8XmcItP3Evw7g4G5fO3GrRhtNyU","success":true}

C:\Users\19638>set RESET=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJxaW5pdS1wcm9qZWN0Iiwic3ViIjoiMSIsImV4cCI6MTc1OTAxNjQyMSwiaWF0IjoxNzU5MDE1NTIxLCJ0eXBlIjoicmVzZXQifQ.WY1vbtrNii0C_3gE8XmcItP3Evw7g4G5fO3GrRhtNyU

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/auth/reset-password ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"reset_token\":\"%RESET%\", \"new_password\":\"new_secure_password\" }"
{"message":"\u5bc6\u7801\u5df2\u66f4\u65b0","success":true}

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/membership ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"user_id\":1001, \"start_date\":\"2025-09-01\", \"expire_date\":\"2026-09-01\", \"status\":\"active\" }"
{"message":"\u65e0\u6743\u9650\u4e3a\u4ed6\u4eba\u521b\u5efa\u4f1a\u5458","success":false}

C:\Users\19638>
C:\Users\19638>curl -X GET http://127.0.0.1:7210/api/membership/1001 ^
More?  -H "Authorization: Bearer %TOKEN%"
{"message":"\u65e0\u6743\u9650\u8bbf\u95ee\u4ed6\u4eba\u4f1a\u5458\u4fe1\u606f","success":false}

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/membership/orders ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"user_id\":1001, \"duration_months\":12, \"amount\":199.99, \"payment_method\":\"wechat\" }"
{"message":"\u65e0\u6743\u9650\u4e3a\u4ed6\u4eba\u521b\u5efa\u8ba2\u5355","success":false}

C:\Users\19638>curl -X GET http://127.0.0.1:7210/api/membership/orders/1001/latest ^
More?  -H "Authorization: Bearer %TOKEN%"
{"message":"\u65e0\u6743\u9650\u8bbf\u95ee\u4ed6\u4eba\u8ba2\u5355","success":false}

C:\Users\19638>curl -X GET "http://127.0.0.1:7210/api/membership/orders/1001/recent?n=5" ^
More?  -H "Authorization: Bearer %TOKEN%"
{"message":"\u65e0\u6743\u9650\u8bbf\u95ee\u4ed6\u4eba\u8ba2\u5355","success":false}

C:\Users\19638>curl -X PUT http://127.0.0.1:7210/api/users/1 ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"full_name\":\"Alice Z.\", \"email\":\"alice_new@example.com\", \"phone_number\":\"13800009999\" }"
{"message":"\u7528\u6237\u4fe1\u606f\u5df2\u66f4\u65b0","success":true}

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/auth/verify-security ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"username\":\"alice123\", \"security_answer1\":\"answer1\", \"security_answer2\":\"answer2\" }"
{"reset_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJxaW5pdS1wcm9qZWN0Iiwic3ViIjoiMSIsImV4cCI6MTc1OTAxNjUxOSwiaWF0IjoxNzU5MDE1NjE5LCJ0eXBlIjoicmVzZXQifQ.EQSEXfZlTvzCI934YZ6BqdFAB7e0QlO3QXxm46ac6j4","success":true}

C:\Users\19638>set RESET=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJxaW5pdS1wcm9qZWN0Iiwic3ViIjoiMSIsImV4cCI6MTc1OTAxNjUxOSwiaWF0IjoxNzU5MDE1NjE5LCJ0eXBlIjoicmVzZXQifQ.EQSEXfZlTvzCI934YZ6BqdFAB7e0QlO3QXxm46ac6j4

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/auth/reset-password ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"reset_token\":\"%RESET%\", \"new_password\":\"new_secure_password\" }"
{"message":"\u5bc6\u7801\u5df2\u66f4\u65b0","success":true}

C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/membership ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"user_id\":1, \"start_date\":\"2025-09-01\", \"expire_date\":\"2026-09-01\", \"status\":\"active\" }"
{"membership_id":1,"message":"\u4f1a\u5458\u4fe1\u606f\u5df2\u521b\u5efa","success":true}

C:\Users\19638>curl -X GET http://127.0.0.1:7210/api/membership/1 ^
More?  -H "Authorization: Bearer %TOKEN%"
{"expire_date":"2026-09-01","membership_id":1,"start_date":"2025-09-01","status":"active","user_id":1}

C:\Users\19638>
C:\Users\19638>curl -X POST http://127.0.0.1:7210/api/membership/orders ^
More?  -H "Authorization: Bearer %TOKEN%" ^
More?  -H "Content-Type: application/json" ^
More?  -d "{ \"user_id\":1, \"duration_months\":12, \"amount\":199.99, \"payment_method\":\"wechat\" }"
{"message":"\u8ba2\u5355\u5df2\u521b\u5efa","order_id":1,"success":true}

C:\Users\19638>
C:\Users\19638>curl -X GET http://127.0.0.1:7210/api/membership/orders/1/latest ^
More?  -H "Authorization: Bearer %TOKEN%"
{"amount":199.99,"duration_months":12,"order_id":1,"payment_method":"wechat","purchase_date":"2025-09-28T07:27:37Z","user_id":1}

C:\Users\19638>curl -X GET "http://127.0.0.1:7210/api/membership/orders/1/recent?n=5" ^
More?  -H "Authorization: Bearer %TOKEN%"
[{"amount":199.99,"duration_months":12,"order_id":1,"payment_method":"wechat","purchase_date":"2025-09-28T07:27:37Z","user_id":1}]