#!/bin/bash
# normalize_names.sh - Normaliza nomes de arquivos
# Remove acentos, espaços duplos, caracteres especiais
# Converte para lowercase com underscores

# Remove set -e para não sair com erro quando apenas mostrando dry-run
set -uo pipefail

APPLY=0
FILES=()

# Parse argumentos
for arg in "$@"; do
    if [[ "$arg" == "--apply" ]]; then
        APPLY=1
    else
        FILES+=("$arg")
    fi
done

if [ ${#FILES[@]} -eq 0 ]; then
    echo "❌ Uso: $0 arquivo1 arquivo2 ... [--apply]"
    echo ""
    echo "Normaliza nomes removendo acentos, espaços e caracteres especiais"
    echo ""
    echo "Opções:"
    echo "  --apply    Aplicar mudanças (padrão: dry-run)"
    exit 1
fi

echo "📝 Normalizando ${#FILES[@]} arquivo(s)..."
echo ""

successful=0
failed=0
skipped=0

for f in "${FILES[@]}"; do
    if [ ! -e "$f" ]; then
        echo "⚠️  '$f' não existe, pulando..."
        ((skipped++))
        continue
    fi
    
    # Extrair diretório e nome base
    dir=$(dirname "$f")
    base=$(basename "$f")
    
    # Normalização:
    # 1. Remover acentos (transliterate)
    # 2. Converter para lowercase
    # 3. Trocar espaços por underscores
    # 4. Remover caracteres não-alfanuméricos (exceto ._-)
    # 5. Remover underscores duplicados
    new_name=$(echo "$base" | \
        (iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null || cat) | \
        tr '[:upper:]' '[:lower:]' | \
        tr ' ' '_' | \
        sed 's/[^a-z0-9._-]//g' | \
        sed 's/__*/_/g') || {
        echo "❌ Erro ao processar: $base"
        ((failed++))
        continue
    }
    
    # Se já está normalizado, pular
    if [ "$base" == "$new_name" ]; then
        echo "✓  $base (já normalizado)"
        ((skipped++))
        continue
    fi
    
    new_path="$dir/$new_name"
    
    # Verificar se destino já existe
    if [ -e "$new_path" ] && [ "$f" != "$new_path" ]; then
        echo "❌ $base → $new_name (arquivo já existe!)"
        ((failed++))
        continue
    fi
    
    echo "✅ $base → $new_name"
    
    if [ $APPLY -eq 1 ]; then
        if mv "$f" "$new_path" 2>/dev/null; then
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
    [ $skipped -gt 0 ] && echo "ℹ️  Pulados (já normalizados): $skipped"
    [ $failed -gt 0 ] && echo "❌ Falharam: $failed"
else
    echo "ℹ️  Modo DRY-RUN (nenhuma mudança aplicada)"
    echo "   Para aplicar, adicione --apply ao comando"
fi

echo "────────────────────────────────────────────────────────────"

exit 0
