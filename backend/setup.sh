#!/bin/bash

# Script de setup do backend

echo "🚀 Configurando backend..."

# Criar ambiente virtual
echo "📦 Criando ambiente virtual..."
python -m venv venv

# Ativar ambiente virtual
echo "✅ Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo "📥 Instalando dependências..."
pip install -r requirements.txt

# Instalar Playwright browsers
echo "🎭 Instalando navegadores do Playwright..."
python -m playwright install chromium

# Copiar .env.example se .env não existir
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️  IMPORTANTE: Edite o arquivo .env e adicione suas chaves de API!"
else
    echo "✅ Arquivo .env já existe"
fi

echo ""
echo "✨ Setup concluído!"
echo ""
echo "Próximos passos:"
echo "1. Edite o arquivo .env com suas chaves de API"
echo "2. Execute: source venv/bin/activate"
echo "3. Execute: uvicorn app.main:app --reload"
