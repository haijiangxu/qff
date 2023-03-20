#  Docker部署

```{admonition} 说明
鉴于QFF的安装涉及数据库及数据运维软件的安装配置，导致用户难以在短时间部署，
为此我们专门设计了Docker镜像，方便您直接拉取使用。
```

## 安装 Docker
[Docker](https://www.docker.com/) 是一个开源的应用容器引擎，可以让开发者打包他们的应用以及依赖包到一个轻量级、
可移植的容器中，然后发布到任何流行的 Linux 机器上，也可以实现虚拟化。

### 安装指导

1. [Docker 安装教程](https://www.runoob.com/docker/docker-tutorial.html)
2. 建议 Windows 7 和 8 的用户升级到 Windows 10/11 系统进行安装
3. [Windows 镜像下载地址](https://msdn.itellyou.cn/)

### 配置国内镜像

1. [Docker 国内镜像加速教程](https://www.runoob.com/docker/docker-mirror-acceleration.html)
2. 请在国内使用的用户务必进行该项配置, 从而加速获取镜像的速度.

(mongoimage)=
## 部署MongoDB镜像

```{important}
由于QFF数据运维需每天定时更新证券数据，强烈建议您配置自己的云服务器或家庭[NAS服务器](https://www.synology.cn/zh-cn/products/skynas),
并将MongoDB和QFF镜像部署到您的服务器上。
```
[Docker安装MongoDB教程](https://www.runoob.com/docker/docker-install-mongodb.html)

### 拉取 mongo 镜像
选择合适的mongo镜像版本，本教程选择镜像体积较小且稳定版本4.2.2，可访问<https://hub.docker.com/_/mongo>了解更多信息。

```
docker pull mongo:4.2.2
```

### 运行 mongo 容器

1. 普通运行:
```
docker run -d -p 27017:27017 mongo:4.2.2
```

2. 指定数据保存路径
如果为方便以后数据库迁移，可以指定容器内数据库文件映射到外部的文件路径:

```
docker run -d  -v /root/db /data/db -p 27017:27017 mongo:4.2.2
```
其中`/root/db`是外部服务器保存数据目录的路径

3. 如果您的数据库不是仅在局域网内使用，基于安全考虑，必须设置账户密码。设置方法如下：
```
docker run -d -v MONGO_INITDB_ROOT_USERNAME admin -v MONGO_INITDB_ROOT_PASSWORD xxxxxx mongo:4.2.2
```
其中`xxxxxx`为您设置的密码。
(qffimage)=
## 部署 QFF 镜像

此镜像会在每次 QFF 更新版本时自动更新


### 拉取 QFF 镜像

```
docker pull haijiangxu/qff
```

### 运行 QFF 容器
1. 普通运行:
```
docker run -d -p 8765:8765 qff
```
2. 如果MongoDB设置了密码，则需做以下配置：
```
docker run -d -p 8765:8765 -v /root/work:/root/work -e MONGODB_URI="mongodb://admin:xxxxxx@localhost/?authSource=admin&authMechanism=SCRAM-SHA-256" qff
```

### 镜像使用

- QFF镜像基于Ubuntu20.04版本OS，安装了QFF及所有依赖库，并安装了cron定时服务，镜像已配置了自动数据更新服务，
  启动QFF容器后，您不用再关心数据更新问题。
  
- QFF镜像还安装了JupyterLab，方便用户直接在浏览器使用。打开本地浏览器输入地址：```http://服务器地址:8765 ```,
显示密码框提示，输入密码:`qff`后，将进入[JupyterLab](https://jupyter.org/try) 界面。
![jupyter-lab](https://jupyter.org/assets/homepage/labpreview.webp)

```{important}
由于QFF目前还处于开发阶段，版本不稳定，在使用docker镜像时，可以在JupyterLab的终端中运行 `pip install -U qff` 升级QFF库版本。 
```