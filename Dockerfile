# Imagen base con Python y CUDA (ajusta a tu versión de GPU/driver)
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

# Variables de entorno
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYOPENGL_PLATFORM=egl
ENV USE_CUDA=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# Forzar arquitecturas CUDA para la compilación de extensiones PyTorch
ENV TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6"

# Usar mirrors oficiales con HTTPS
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|https://archive.ubuntu.com/ubuntu/|g' /etc/apt/sources.list \
    && sed -i 's|http://security.ubuntu.com/ubuntu/|https://security.ubuntu.com/ubuntu/|g' /etc/apt/sources.list \
    && apt-get update -o Acquire::ForceIPv4=true \
    && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        cmake \
        ninja-build \
        libgl1 \
        libglib2.0-0 \
        libosmesa6-dev \
        libglu1-mesa \
        libgl1-mesa-dri \
        libegl1 \
        libgles2-mesa-dev \
        mesa-utils \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        curl \
        ca-certificates \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel cmake ninja

RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-runtime-12-4

# Instalar PyTorch con CUDA (ajusta según tu GPU/driver)
RUN pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124

# Instalar el resto de dependencias
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Reinstalar uv_unwrapper y texture_baker desde el código fuente local
RUN pip uninstall -y uv_unwrapper texture_baker || true \
    && cd uv_unwrapper && python setup.py clean --all && pip install . && cd .. \
    && cd texture_baker && python setup.py clean --all && pip install . && cd ..

# Exponer puerto de la API
EXPOSE 8080

# CMD que precalienta modelo en runtime (local o Cloud Run)
CMD ["python", "app.py"]
