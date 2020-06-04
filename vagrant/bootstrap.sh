#!/usr/bin/env bash

ON_TX2=0

sudo apt-get update

sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password password'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password password'
sudo apt-get -y install mysql-server

sudo apt-get install -y mysql-server
sudo apt-get install -y libmysqlclient-dev
sudo apt-get install -y libsm6 libxext6 libxrender1

sudo apt-get install -y python3-pip

sudo pip3 install numpy
if [[ ${ON_TX2} -eq 0 ]]; then
    sudo pip3 install tensorflow
    sudo pip3 install flask
    sudo pip3 install flask-sqlalchemy
else
    sudo pip3 install tensorflow-1.3.0-cp35-cp35m-linux_aarch64.whl
fi

sudo pip3 install mysqlclient
sudo pip3 install opencv-python


mysql -u root -ppassword -e "create database entries;"
mysql -u root -ppassword "entries" -e "create table vehicle_entries(id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,  capture_time datetime, category VARCHAR(50));"