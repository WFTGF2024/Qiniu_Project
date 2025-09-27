## 文件服务器
这个部分可有可无，我把它独立了出来。如果公网服务器本身可以支持通过URL让别人下载文件，这一个可以省略。

由于部署AI后端的GPU服务器费用较高，按量付费。文件这部分也较为独立，把文件服务器放在CPU服务器上节省开销。

### 1. 上传文件 `test.wav`

```cmd
curl -X POST http://127.0.0.1:7201/upload/2 -F "file=@test.wav"
```


```json
{
  "filename": "test.wav",
  "message": "File uploaded successfully"
}
```

---

### 2. 查看用户 2 的所有文件

```cmd
curl -X GET http://127.0.0.1:7201/files/2
```


```json
[
  {
    "file_id": 1,
    "filename": "test.wav"
  }
]

```


### 3. 下载文件（设`file_id=2`）

```cmd
curl -X GET http://127.0.0.1:7201/download/1 -o downloaded_test.wav
```
会把文件保存为 `downloaded_test.wav`。

### 4. 删除文件（设 `file_id=1`）

```cmd
curl -X DELETE http://127.0.0.1:7201/files/1
```

```json
{"message": "File deleted successfully"}
```


### 5. 批量上传多个文件

```cmd
curl -X POST http://127.0.0.1:7201/upload/2 -F "file=@test.wav" -F "file=@readme.txt"
```

