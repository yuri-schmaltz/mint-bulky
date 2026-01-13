#!/bin/bash
# extract_id3.sh - Extrai metadados ID3 de MP3 e gera lista de renomeação
# Formato: <artista>_-_<título>.mp3

set -euo pipefail

APPLY=0
DIRECTORY="."

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --apply)
            APPLY=1
            shift
            ;;
        *)
            DIRECTORY="$1"
            shift
            ;;
    esac
done

if [ ! -d "$DIRECTORY" ]; then
    echo "❌ Erro: '$DIRECTORY' não é um diretório válido"
    exit 1
fi

# Verificar dependências
if ! command -v ffprobe &> /dev/null; then
    echo "❌ ffprobe não encontrado. Instale com:"
    echo "   sudo apt install ffmpeg"
    exit 1
fi

echo "🎵 Processando arquivos MP3 em: $DIRECTORY"
echo ""

successful=0
failed=0

# Função para limpar strings de metadados
clean_string() {
    echo "$1" | \
        iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null | \
        sed 's/[^a-zA-Z0-9 _-]//g' | \
        tr ' ' '_' | \
        sed 's/__*/_/g'
}

shopt -s nullglob
for mp3_file in "$DIRECTORY"/*.mp3 "$DIRECTORY"/*.MP3; do
    [ ! -f "$mp3_file" ] && continue
    
    base=$(basename "$mp3_file")
    
    # Extrair artista e título com ffprobe
    artist=$(ffprobe -v quiet -show_entries format_tags=artist -of default=noprint_wrappers=1:nokey=1 "$mp3_file" 2>/dev/null | head -1)
    title=$(ffprobe -v quiet -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$mp3_file" 2>/dev/null | head -1)
    
    # Fallback se não tiver metadados
    if [ -z "$artist" ] || [ -z "$title" ]; then
        echo "⚠️  $base (sem metadados ID3 completos)"
        ((failed++))
        continue
    fi
    
    # Limpar strings
    artist_clean=$(clean_string "$artist")
    title_clean=$(clean_string "$title")
    
    new_name="${artist_clean}_-_${title_clean}.mp3"
    new_path="$(dirname "$mp3_file")/$new_name"
    
    # Verificar colisão
    if [ -e "$new_path" ] && [ "$mp3_file" != "$new_path" ]; then
        echo "❌ $base → $new_name (arquivo já existe!)"
        ((failed++))
        continue
    fi
    
    echo "✅ $base"
    echo "   → $new_name"
    
    if [ $APPLY -eq 1 ]; then
        if mv "$mp3_file" "$new_path" 2>/dev/null; then
            ((successful++))
        else
            echo "   ❌ Erro ao renomear"
            ((failed++))
        fi
    fi
done

echo ""
echo "────────────────────────────────────────────────────────────"

if [ $APPLY -eq 1 ]; then
    echo "✅ Renomeados com sucesso: $successful"
    [ $failed -gt 0 ] && echo "❌ Falharam ou sem metadados: $failed"
else
    echo "ℹ️  Modo DRY-RUN (nenhuma mudança aplicada)"
    echo "   Para aplicar, execute: $0 $DIRECTORY --apply"
fi

echo "────────────────────────────────────────────────────────────"
