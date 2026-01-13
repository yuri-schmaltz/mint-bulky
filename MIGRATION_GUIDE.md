# Guia de Migração para o Bulky

Este documento oferece um roteiro prático para migrar suas regras de renomeação do **KRename**, **GPRename**, **Thunar Bulk Rename**, **pyRenamer** e outras ferramentas para o **Bulky**.

---

## Índice

1. [Princípios de Migração](#princípios-de-migração)
2. [Migração desde KRename](#migração-desde-krename)
3. [Migração desde GPRename](#migração-desde-gprename)
4. [Migração desde Thunar Bulk Rename](#migração-desde-thunar-bulk-rename)
5. [Migração desde pyRenamer](#migração-desde-pyrenamer)
6. [Migração desde Métodos CLI](#migração-desde-métodos-cli)
7. [Scripts Auxiliares](#scripts-auxiliares)
8. [Casos de Uso Avançados](#casos-de-uso-avançados)
9. [Troubleshooting](#troubleshooting)

---

## Princípios de Migração

### Filosofia do Bulky
- **Operações focadas**: Substituir, Remover, Inserir, Alterar Caixa
- **Preview obrigatório**: Sempre visualize antes de executar
- **Escopo explícito**: Nome, Extensão ou Completo
- **Numeração via placeholders**: `%n`, `%0n`, `%00n`, `%000n`...
- **Sem metadados nativos**: EXIF/ID3 requerem pré-processamento

### Estratégia Geral
1. **Identifique a operação principal** (substituir, inserir, remover, caixa)
2. **Mapeie tokens/placeholders** para o formato do Bulky
3. **Teste com poucos arquivos** primeiro
4. **Use escopo correto** (Nome vs Extensão vs Completo)
5. **Para metadados**, extraia antes com ferramentas CLI

---

## Migração desde KRename

### Tabela de Equivalências de Tokens

| Token KRename | Equivalente Bulky | Notas |
|---------------|-------------------|-------|
| `[name]` | (nome original) | Use escopo "Nome" |
| `[extension]` | (extensão original) | Use escopo "Extensão" |
| `%&` | `%n` | Contador simples |
| `%#` | `%0n` | Contador com 1 zero |
| `%##` | `%00n` | Contador com 2 zeros |
| `%###` | `%000n` | Contador com 3 zeros |
| `[upper]` | Op: "Alterar caixa" → MAIÚSCULAS | — |
| `[lower]` | Op: "Alterar caixa" → minúsculas | — |
| `[capitalize]` | Op: "Alterar caixa" → Primeira maiúscula | — |
| `[length]` | ❌ Não suportado | Use script externo |
| `[trimmed]` | Op: "Remover" ou regex `^\s+\|\s+$` | Remover espaços |
| `[exif:*]` | ❌ Não nativo | Ver [Metadados EXIF](#metadados-exif) |
| `[mp3:*]` | ❌ Não nativo | Ver [Metadados ID3](#metadados-id3) |
| `[date]` | ❌ Não nativo | Ver [Data/Hora](#datahora) |
| `[filesize]` | ❌ Não nativo | Use script externo |

### Exemplos de Migração

#### Exemplo 1: Numeração com Prefixo
**KRename**: `Foto_[##].jpg` (contador 2 dígitos)

**Bulky**:
1. **Operação**: "Substituir"
   - **Buscar**: `*` (tudo)
   - **Substituir por**: `Foto_%00n`
   - **Início**: 1, **Incremento**: 1
2. **Escopo**: "Nome"

---

#### Exemplo 2: Uppercase + Contador
**KRename**: `[upper][name]_[#].txt`

**Bulky** (duas passadas):
1. **Primeira**: Op: "Alterar caixa" → MAIÚSCULAS, Escopo: "Nome"
2. **Segunda**: Op: "Inserir" → `_%0n` na posição final (reverso=1)

*Ou use regex em uma passada*:
- **Substituir** regex: `(.+)` → `\U\1_%0n` (se seu Python suporta `\U`)

---

#### Exemplo 3: Remover Texto Específico
**KRename**: Plugin "Replace" — remover `[download]`

**Bulky**:
1. **Operação**: "Substituir"
   - **Buscar**: `[download]`
   - **Substituir por**: (vazio)
   - **Case**: marcado
2. **Escopo**: "Completo"

---

### Metadados EXIF

**KRename**: `[exif:DateTimeOriginal]_[name].jpg`

**Solução Bulky**:
```bash
# 1. Extrair data EXIF e renomear com exiftool
exiftool -d '%Y%m%d_%H%M%S' '-FileName<${DateTimeOriginal}_${FileName}' *.jpg

# OU: Gerar lista de nomes com Python e importar no Bulky
python3 << 'EOF'
import os
from datetime import datetime
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("Instale Pillow: pip install Pillow")
    exit(1)

for fname in os.listdir('.'):
    if fname.lower().endswith(('.jpg', '.jpeg')):
        try:
            img = Image.open(fname)
            exif = img._getexif()
            if exif:
                for tag, value in exif.items():
                    if TAGS.get(tag) == 'DateTimeOriginal':
                        dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        new_name = dt.strftime('%Y%m%d_%H%M%S') + '_' + fname
                        print(f"{fname} → {new_name}")
                        # os.rename(fname, new_name)  # Descomente para aplicar
        except Exception as e:
            print(f"Erro em {fname}: {e}")
EOF
```

---

### Metadados ID3

**KRename**: `[mp3:artist]_-_[mp3:title].mp3`

**Solução Bulky**:
```bash
# Usando eyeD3 ou id3v2
for f in *.mp3; do
    artist=$(id3v2 -l "$f" | grep -oP 'TPE1.*: \K.*')
    title=$(id3v2 -l "$f" | grep -oP 'TIT2.*: \K.*')
    new_name="${artist}_-_${title}.mp3"
    echo "$f → $new_name"
    # mv "$f" "$new_name"  # Descomente para aplicar
done

# OU use ffprobe (mais robusto)
for f in *.mp3; do
    artist=$(ffprobe -v quiet -show_entries format_tags=artist -of default=noprint_wrappers=1:nokey=1 "$f")
    title=$(ffprobe -v quiet -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$f")
    new_name="${artist}_-_${title}.mp3"
    echo "$f → $new_name"
    # mv "$f" "$new_name"
done
```

---

### Data/Hora

**KRename**: `[date:yyyy-MM-dd]_[name].txt`

**Solução Bulky**:
```bash
# Prefixar com data de modificação
for f in *; do
    date=$(date -r "$f" '+%Y-%m-%d')
    new_name="${date}_${f}"
    echo "$f → $new_name"
    # mv "$f" "$new_name"
done
```

Depois ajuste no Bulky se necessário (ex.: remover sufixos, alterar caixa).

---

## Migração desde GPRename

### Mapeamento de Operações

| Operação GPRename | Operação Bulky | Configuração |
|-------------------|----------------|--------------|
| **Replace** | Substituir | Buscar/Substituir |
| **Insert** | Inserir | Texto + Posição |
| **Delete from-to** | Remover | De/Até (normal/reverso) |
| **Numbering** | Inserir | `%n` com início/incremento |
| **Uppercase** | Alterar caixa | MAIÚSCULAS |
| **Lowercase** | Alterar caixa | minúsculas |
| **Capitalize** | Alterar caixa | Primeira maiúscula |

### Exemplos

#### Exemplo 1: Inserir Prefixo
**GPRename**: Insert "Backup_" at position 0

**Bulky**:
1. **Operação**: "Inserir"
   - **Texto**: `Backup_`
   - **Posição**: 1
   - **Reverso**: desmarcar
2. **Escopo**: "Nome"

---

#### Exemplo 2: Substituir com Numeração
**GPRename**: Replace "file" → "doc" + Numbering start=10

**Bulky** (duas passadas):
1. **Substituir**: `file` → `doc`
2. **Inserir**: `_%00n` (Início=10, Incremento=1)

*Ou em uma passada*:
- **Substituir**: `file` → `doc_%00n` (Início=10)

---

#### Exemplo 3: Remover Primeiros 5 Caracteres
**GPRename**: Delete from 0 to 5

**Bulky**:
1. **Operação**: "Remover"
   - **De**: 1
   - **Até**: 5
   - **De reverso**: desmarcar
   - **Até reverso**: desmarcar
2. **Escopo**: "Nome"

---

## Migração desde Thunar Bulk Rename

### Mapeamento de Padrões

| Padrão Thunar | Equivalente Bulky | Notas |
|---------------|-------------------|-------|
| `[N]` | `%n` | Contador |
| `[NN]` | `%0n` | 2 dígitos |
| `[NNN]` | `%00n` | 3 dígitos |
| `[NNNN]` | `%000n` | 4 dígitos |
| Buscar/Substituir | "Substituir" | — |
| Insert/Overwrite | "Inserir" + sobrescrever | Marcar "Sobrescrever" |
| Uppercase/Lowercase | "Alterar caixa" | — |

### Exemplo: Renomear com Data
**Thunar**: `Documento [YYYY-MM-DD].txt` (necessita plugin/script)

**Bulky + Script**:
```bash
# Pré-processamento
for f in *.txt; do
    date=$(date '+%Y-%m-%d')
    new_name="Documento ${date}.txt"
    echo "$f → $new_name"
    # mv "$f" "$new_name"
done
```

Depois use Bulky para ajustes finos (ex.: adicionar contador).

---

## Migração desde pyRenamer

### Mapeamento de Placeholders

| pyRenamer | Bulky | Notas |
|-----------|-------|-------|
| `{#}` | `%n` | Contador |
| `{##}` | `%0n` | 2 dígitos |
| `{###}` | `%00n` | 3 dígitos |
| `{X}` | Escopo "Nome" | Nome original |
| `{C}` | ❌ Não nativo | Diretório — use script |
| Manual patterns | "Substituir" + regex | — |

### Exemplo: Padrão Complexo
**pyRenamer**: `{X}_{###}.jpg` (nome original + contador 3 dígitos)

**Bulky**:
1. **Operação**: "Inserir"
   - **Texto**: `_%000n`
   - **Posição**: reverso 1 (antes da extensão)
   - **Início**: 1, **Incremento**: 1
2. **Escopo**: "Nome"

---

## Migração desde Métodos CLI

### `rename` (Perl)

**Exemplo**: `rename 's/foo/bar/g' *.txt`

**Bulky**:
1. **Operação**: "Substituir"
   - **Buscar**: `foo`
   - **Substituir por**: `bar`
   - **Regex**: marcar
2. **Escopo**: "Completo"

---

### `mmv`

**Exemplo**: `mmv "*.JPG" "#1.jpg"` (lowercase extension)

**Bulky**:
1. **Operação**: "Alterar caixa" → minúsculas
2. **Escopo**: "Extensão"

---

### Loop `for` no Bash

**Exemplo**:
```bash
for f in *.log; do
    mv "$f" "${f%.log}_backup.log"
done
```

**Bulky**:
1. **Operação**: "Inserir"
   - **Texto**: `_backup`
   - **Posição**: reverso 1
2. **Escopo**: "Nome"

---

## Scripts Auxiliares

### Script 1: Converter Lista de Renomeações para Bulky

Se você tem um arquivo `rename_list.txt`:
```
old_name1.txt → new_name1.txt
old_name2.txt → new_name2.txt
```

Aplicar com:
```bash
#!/bin/bash
while IFS=' → ' read -r old new; do
    if [ -f "$old" ]; then
        echo "Renomeando: $old → $new"
        mv "$old" "$new"
    fi
done < rename_list.txt
```

---

### Script 2: Pré-processar EXIF em Lote

```python
#!/usr/bin/env python3
"""
Renomeia fotos com EXIF DateTimeOriginal
Uso: python3 rename_exif.py /caminho/fotos
"""
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("Erro: Instale Pillow com 'pip install Pillow'")
    sys.exit(1)

def get_exif_date(image_path):
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if TAGS.get(tag) == 'DateTimeOriginal':
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        print(f"Erro ao ler EXIF de {image_path}: {e}")
    return None

def main(directory):
    directory = Path(directory)
    counter = 1
    
    for img_file in sorted(directory.glob('*.jpg')) + sorted(directory.glob('*.jpeg')) + sorted(directory.glob('*.JPG')) + sorted(directory.glob('*.JPEG')):
        exif_date = get_exif_date(img_file)
        
        if exif_date:
            new_name = f"{exif_date.strftime('%Y%m%d_%H%M%S')}_{counter:03d}{img_file.suffix.lower()}"
        else:
            new_name = f"IMG_{counter:04d}{img_file.suffix.lower()}"
        
        new_path = img_file.parent / new_name
        print(f"{img_file.name} → {new_name}")
        
        # Descomente para aplicar:
        # img_file.rename(new_path)
        counter += 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <diretório>")
        sys.exit(1)
    main(sys.argv[1])
```

**Uso**:
```bash
chmod +x rename_exif.py
./rename_exif.py ~/Fotos/Ferias2024
# Verifique a saída, depois descomente a linha 'img_file.rename(new_path)'
```

---

### Script 3: Normalizar Nomes de Arquivos

Remove caracteres problemáticos, espaços extras, acentos:

```bash
#!/bin/bash
# normalize_names.sh
# Uso: ./normalize_names.sh *.txt

for f in "$@"; do
    # Remover espaços duplos, acentos, caracteres especiais
    new_name=$(echo "$f" | \
        iconv -f utf8 -t ascii//TRANSLIT | \
        tr -s ' ' '_' | \
        tr '[:upper:]' '[:lower:]' | \
        sed 's/[^a-z0-9._-]//g')
    
    if [ "$f" != "$new_name" ]; then
        echo "$f → $new_name"
        # mv "$f" "$new_name"  # Descomente para aplicar
    fi
done
```

---

### Script 4: Renomear Baseado em Hash (Deduplicação)

```python
#!/usr/bin/env python3
"""
Renomeia arquivos com hash SHA256 (útil para deduplicação)
Uso: python3 rename_by_hash.py /caminho/arquivos
"""
import sys
import hashlib
from pathlib import Path

def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()[:16]  # Primeiros 16 caracteres

def main(directory):
    directory = Path(directory)
    
    for file_path in directory.iterdir():
        if file_path.is_file():
            file_hash = hash_file(file_path)
            new_name = f"{file_hash}{file_path.suffix}"
            new_path = file_path.parent / new_name
            
            print(f"{file_path.name} → {new_name}")
            # Descomente para aplicar:
            # file_path.rename(new_path)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <diretório>")
        sys.exit(1)
    main(sys.argv[1])
```

---

## Casos de Uso Avançados

### Caso 1: Reorganizar Estrutura de Data no Nome

**Objetivo**: `2024-01-15_relatorio.pdf` → `relatorio_20240115.pdf`

**Bulky**:
1. **Operação**: "Substituir"
   - **Buscar** (regex): `^(\d{4})-(\d{2})-(\d{2})_(.+)$`
   - **Substituir por**: `\4_\1\2\3`
   - **Regex**: ✅
2. **Escopo**: "Nome"

---

### Caso 2: Adicionar Sufixo Baseado em Condição

**Objetivo**: Arquivos > 1MB recebem `_large`, outros `_small`

**Script**:
```bash
for f in *; do
    if [ -f "$f" ]; then
        size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
        if [ "$size" -gt 1048576 ]; then
            suffix="_large"
        else
            suffix="_small"
        fi
        
        base="${f%.*}"
        ext="${f##*.}"
        
        if [ "$base" != "$ext" ]; then
            new_name="${base}${suffix}.${ext}"
        else
            new_name="${f}${suffix}"
        fi
        
        echo "$f → $new_name"
        # mv "$f" "$new_name"
    fi
done
```

Depois ajuste no Bulky se necessário.

---

### Caso 3: Série de TV com Padrão Complexo

**Objetivo**: `Breaking.Bad.S01E01.720p.x264.mkv` → `Breaking_Bad_S01E01.mkv`

**Bulky** (múltiplas passadas):
1. **Substituir**: `.` → `_` (literal)
2. **Substituir** (regex): `_\d+p.*\.mkv$` → `.mkv` (remove qualidade/codec)

*Ou tudo em um regex*:
```regex
Buscar: ^(.+?)\.S(\d+)E(\d+)\..+\.mkv$
Substituir: \1_S\2E\3.mkv
```

---

### Caso 4: Prefixo Incremental com Timestamp

**Objetivo**: `relatorio.pdf` → `20240115_001_relatorio.pdf`

**Script**:
```bash
date_prefix=$(date '+%Y%m%d')
counter=1

for f in *.pdf; do
    new_name="${date_prefix}_$(printf '%03d' $counter)_${f}"
    echo "$f → $new_name"
    # mv "$f" "$new_name"
    ((counter++))
done
```

---

## Troubleshooting

### Problema 1: Colisão de Nomes

**Sintoma**: Bulky avisa "Name collision on 'arquivo.txt'"

**Soluções**:
- Use numeração: adicione `%n` no final
- Mude escopo: se estava em "Completo", tente "Nome"
- Adicione contador único: `_%00n` com incremento 1

---

### Problema 2: Regex Não Funciona

**Sintoma**: Padrão não captura

**Checklist**:
- ✅ Marcou "Regex" na interface?
- ✅ Testou em https://regex101.com primeiro?
- ✅ Escapou caracteres especiais? (`.` → `\.`, `*` → `\*`)
- ✅ Grupos de captura corretos? `\1`, `\2`... (não `$1`)

**Exemplo**:
```
Errado:  Buscar *.txt  (literal)
Certo:   Buscar .+\.txt (regex) OU marcar "Regex" desligado e usar *
```

---

### Problema 3: Caracteres Especiais Quebram Nomes

**Sintoma**: Erros ao renomear arquivos com `[`, `]`, `(`, `)`, `&`

**Solução**: Escape ou substitua antes:
```bash
# Pré-processar com script
for f in *; do
    new_name=$(echo "$f" | sed 's/[][()&]/_/g')
    if [ "$f" != "$new_name" ]; then
        mv "$f" "$new_name"
    fi
done
```

---

### Problema 4: Bulk Rename Não Lista Alguns Arquivos

**Sintoma**: Arquivos não aparecem ao adicionar diretório

**Causas**:
- Permissões: Bulky não tem acesso
- Arquivos ocultos: não são adicionados automaticamente
- Symlinks quebrados: FileObject.is_valid = False

**Solução**:
```bash
# Verificar permissões
ls -la /caminho/arquivos

# Adicionar explicitamente (via CLI ou script)
bulky arquivo1.txt arquivo2.txt arquivo_oculto.txt
```

---

### Problema 5: Perda de Metadados

**Sintoma**: Após renomear, EXIF/tags desaparecem

**Causa**: Bulky usa `Gio.File.set_display_name()`, que preserva metadados. Mas alguns filesystems/protocolos remotos podem não suportar.

**Solução**:
- Para arquivos locais: metadados são preservados
- Para remotos: teste antes ou use ferramentas especializadas (`exiftool -preserve`)

---

## Checklist Final de Migração

- [ ] Identifiquei a operação principal (substituir/inserir/remover/caixa)
- [ ] Mapeei tokens/placeholders para formato Bulky
- [ ] Testei com 2-3 arquivos de amostra
- [ ] Validei escopo (Nome vs Extensão vs Completo)
- [ ] Para metadados, usei pré-processamento com script
- [ ] Verifiquei pré-visualização antes de renomear
- [ ] Fiz backup ou testei em cópia dos arquivos
- [ ] Documentei a regra para reuso futuro

---

## Recursos Adicionais

- **Bulky Issues**: https://github.com/linuxmint/bulky/issues
- **Regex101**: https://regex101.com (testar regex)
- **ExifTool**: https://exiftool.org (metadados)
- **FFprobe**: https://ffmpeg.org/ffprobe.html (áudio/vídeo)

---

**Contribua**: Tem uma regra complexa que migrou com sucesso? Abra uma PR adicionando ao [COMPARATIVO.md](COMPARATIVO.md) ou a este guia!

**Última atualização**: 2026-01-12
