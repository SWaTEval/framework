# SWaTEval Framework

This repository has been published as a part of the following paper. Please consider citing this paper if you use our work in your research.

> Borcherding, A.; Penkov, N.; Giraud, M. and Beyerer, J. (2023). SWaTEval: An Evaluation Framework for Stateful Web Application Testing. In Proceedings of the 9th International Conference on Information Systems Security and Privacy - ICISSP

## Setup

**Note:** The project runs under Python 3.8 

1. To setup a conda environment in Linux run:

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x ./Miniconda3-latest-Linux-x86_64.sh
bash ./Miniconda3-latest-Linux-x86_64.sh
```

2. Create and activate a virtual environment for Python 3.8:

```
conda create -n "scanner" python=3.8
conda activate scanner
```

3. Install the requirements:

```
pip install -r requirements.txt
```

4. Create a Docker image of the [evaluation-target](https://github.com/SWaTEval/evaluation-target) by following the steps described in its repository

5. Run the needed Docker containers using [Docker Compose](https://docs.docker.com/compose/): 


```
docker compose up
```

6. Install [Docker DNS-Gen](https://github.com/jderusse/docker-dns-gen) to create a DNS server in Docker

```
sudo sh -c "$(curl -fsSL https://raw.githubusercontent.com/jderusse/docker-dns-gen/master/bin/install)"
```

7. Run the SWaTEval framework:

```
python main.py
```
