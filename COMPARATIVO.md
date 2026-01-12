# Comparativo: Bulky vs KRename vs GPRename

## Visão Geral

| Ferramenta | Descrição | Melhor Para |
|------------|-----------|-------------|
| **Bulky** | Renomeador gráfico moderno (XApp), focado em tarefas comuns com pré-visualização clara | Usuários que querem rapidez, interface limpa e operações bem cobertas sem complexidade excessiva |
| **KRename** | Ferramenta avançada KDE com dezenas de tokens, plugins e perfis | Power users que precisam de metadados (EXIF/ID3), regras complexas encadeadas e automação |
| **GPRename** | Leve e tradicional (GTK), interface simples | Operações básicas rápidas em ambientes leves |

---

## Funcionalidades por Categoria

### 1. Operações de Renomeação

#### Bulky
- ✅ **Substituir texto**: literal com curingas (`*`, `?`) ou regex completo
- ✅ **Remover**: intervalo de caracteres (do início/fim)
- ✅ **Inserir**: texto/contador em posição específica (normal/reverso, com sobrescrita)
- ✅ **Alterar caixa**: Título, MAIÚSCULAS, minúsculas, Primeira maiúscula
- ✅ **Remover acentos**: normalização Unicode via unidecode
- ✅ **Escopo configurável**: Nome, Extensão ou Completo
- ✅ **Numeração flexível**: `%n`, `%0n`, `%00n`, `%000n` com início e incremento

#### KRename
- ✅ Todas as operações acima
- ✅ **Perfis reutilizáveis**: salve conjuntos de regras
- ✅ **Múltiplas etapas**: encadeie regras complexas
- ✅ **Copiar/Mover/Symlink**: durante o processo de renomeação
- ✅ **Tokens avançados**: EXIF, ID3/OGG, datas, tamanho, hash, permissões

#### GPRename
- ✅ Substituir, inserir, remover básicos
- ✅ Numeração simples
- ✅ Alterar caixa
- ⚠️ Regex limitado em algumas versões
- ❌ Sem metadados EXIF/ID3 nativos

---

### 2. Correspondência e Expressões

| Recurso | Bulky | KRename | GPRename |
|---------|-------|---------|----------|
| Busca literal | ✅ | ✅ | ✅ |
| Curingas (`*`, `?`) | ✅ | ✅ | ⚠️ Limitado |
| Regex completo | ✅ | ✅ | ⚠️ Básico |
| Case sensitive/insensitive | ✅ | ✅ | ✅ |
| Grupos de captura | ✅ (via regex) | ✅ | ❌ |

---

### 3. Metadados e Tokens

| Tipo | Bulky | KRename | GPRename |
|------|-------|---------|----------|
| Nome/Extensão | ✅ | ✅ | ✅ |
| Numeração/Contador | ✅ | ✅ | ✅ |
| EXIF (foto) | ❌* | ✅ | ❌ |
| ID3/OGG (áudio) | ❌* | ✅ | ❌ |
| Data/Hora arquivo | ❌* | ✅ | ⚠️ |
| Tamanho/Hash | ❌* | ✅ | ❌ |

*\* Bulky foca em operações de texto; para metadados, extraia com ferramentas externas (`exiftool`, `ffprobe`) e incorpore via Inserir/Substituir.*

---

### 4. Pré-visualização e Segurança

#### Bulky
- ✅ **Pré-visualização por item**: cada linha mostra "Nome" → "Novo nome"
- ✅ **Detecção de colisão**: avisa se dois arquivos terão o mesmo nome
- ✅ **Checagem de permissões**: valida escrita no arquivo e no diretório pai
- ✅ **Ordem segura**: arquivos antes, diretórios do mais profundo ao raso
- ✅ **Renomeação assíncrona**: não trava a interface em lotes grandes
- ✅ **Cache de thumbnails**: persistente em `~/.cache/bulky/thumbnails`

#### KRename
- ✅ Pré-visualização rica com múltiplas colunas
- ✅ Fluxo em etapas: origem → regras → destino
- ✅ Modo simulação (dry-run)
- ✅ Pode copiar/mover em vez de renomear

#### GPRename
- ✅ Pré-visualização simples
- ⚠️ Menos validações automáticas
- ✅ Aplicação direta e rápida

---

### 5. UX e Integração

| Aspecto | Bulky | KRename | GPRename |
|---------|-------|---------|----------|
| Desktop | Cinnamon, MATE, GNOME, Xfce* | KDE/Plasma (ideal), outros | Qualquer GTK |
| Drag & Drop | ✅ | ✅ | ✅ |
| Atalhos | ✅ (Ctrl+N, Ctrl+D, Ctrl+Q/W, F1) | ✅ | ⚠️ Limitado |
| Thumbnails | ✅ (lazy-load + cache) | ✅ | ⚠️ Básico |
| Interface | Minimalista, moderna | Rica, múltiplas abas | Tradicional, simples |
| Integração File Manager | ✅ (Nemo, Caja) | ✅ (Dolphin) | ⚠️ Manual |

*\* Bulky é redundante no Xfce (Thunar tem renomeador embutido).*

---

### 6. Desempenho

| Métrica | Bulky | KRename | GPRename |
|---------|-------|---------|----------|
| Startup | ~780ms (GUI ready) | ~1-2s (carrega plugins) | ~500ms |
| Memória idle | ~44MB RSS | ~80-120MB | ~30MB |
| Throughput rename | ~48k arquivos/s* | ~30-40k/s | ~50k/s |
| Responsividade UI | ✅ Assíncrono | ⚠️ Pode travar | ✅ Leve |

*\* Medido em SSD, operações simples; varia com IO e complexidade das regras.*

---

## Exemplos Práticos no Bulky

### Exemplo 1: Normalizar Fotos de Férias
**Cenário**: Você tem `IMG_1234.jpg`, `IMG_1235.JPG`, `IMG_1236.jpeg`  
**Objetivo**: `ferias2024_001.jpg`, `ferias2024_002.jpg`, `ferias2024_003.jpg`

**Passos**:
1. Adicione os arquivos ao Bulky (Ctrl+N ou arrastar)
2. **Operação**: "Substituir"
   - **Buscar**: `IMG_*` (curinga captura qualquer coisa após IMG_)
   - **Substituir por**: `ferias2024_%00n`
   - **Início**: 1, **Incremento**: 1
   - **Case**: desmarcar (para ignorar .jpg vs .JPG)
3. **Escopo**: "Nome" (preserva extensões)
4. **Renomear** (verifica pré-visualização antes!)

**Resultado**: Todas viram `ferias2024_001.jpg`, `ferias2024_002.jpg`, etc., mantendo a extensão original normalizada.

---

### Exemplo 2: Remover Prefixo de Downloads
**Cenário**: `[Site] Documento 1.pdf`, `[Site] Planilha.xlsx`  
**Objetivo**: `Documento 1.pdf`, `Planilha.xlsx`

**Passos**:
1. **Operação**: "Substituir"
   - **Buscar**: `[Site] `
   - **Substituir por**: (deixar vazio)
   - **Regex**: desmarcar
   - **Case**: marcar
2. **Escopo**: "Completo" (afeta nome + extensão)
3. **Renomear**

**Resultado**: Remove `[Site] ` de todos os nomes.

---

### Exemplo 3: Adicionar Contador no Início
**Cenário**: `episodio1.mp4`, `episodio2.mp4`  
**Objetivo**: `S01E01_episodio1.mp4`, `S01E02_episodio2.mp4`

**Passos**:
1. **Operação**: "Inserir"
   - **Texto**: `S01E%0n_`
   - **Posição**: 1 (início)
   - **Início**: 1, **Incremento**: 1
   - **Reverso**: desmarcar
2. **Escopo**: "Nome"
3. **Renomear**

**Resultado**: Prefixo `S01E01_`, `S01E02_` adicionado.

---

### Exemplo 4: Alterar Extensões para Minúsculas
**Cenário**: `foto.JPG`, `video.MP4`  
**Objetivo**: `foto.jpg`, `video.mp4`

**Passos**:
1. **Operação**: "Alterar caixa"
   - Selecionar **minúsculas**
2. **Escopo**: "Extensão"
3. **Renomear**

**Resultado**: Extensões viram `.jpg`, `.mp4`; nomes preservados.

---

### Exemplo 5: Remover Acentos (Normalização)
**Cenário**: `relatório_março.pdf`, `apresentação.pptx`  
**Objetivo**: `relatorio_marco.pdf`, `apresentacao.pptx`

**Passos**:
1. **Operação**: "Alterar caixa"
   - Selecionar **Remover acentos**
2. **Escopo**: "Completo"
3. **Renomear**

**Resultado**: `ç` → `c`, `ã` → `a`, `ó` → `o`, etc.

---

### Exemplo 6: Regex Avançado – Reorganizar Data
**Cenário**: `2024-01-15_nota.txt`, `2024-02-20_recibo.pdf`  
**Objetivo**: `nota_15-01-2024.txt`, `recibo_20-02-2024.pdf`

**Passos**:
1. **Operação**: "Substituir"
   - **Buscar** (regex): `(\d{4})-(\d{2})-(\d{2})_(.+)`
   - **Substituir por**: `\4_\3-\2-\1`
   - **Regex**: ✅ marcar
   - **Case**: tanto faz
2. **Escopo**: "Nome"
3. **Renomear**

**Resultado**: Grupos capturados reordenados: `\1`=ano, `\2`=mês, `\3`=dia, `\4`=resto.

---

## Roteiro de Migração: KRename → Bulky

### Regras Comuns e Equivalentes

| Regra no KRename | Equivalente no Bulky | Notas |
|------------------|----------------------|-------|
| `[name]` + numeração | Operação "Inserir" com `%n` | Use início/incremento |
| Token `%&` (contador) | `%0n`, `%00n`, `%000n` | Padding com zeros |
| Substituir texto literal | "Substituir" + busca literal | Curingas `*`/`?` ok |
| Substituir regex | "Substituir" + marcar Regex | Suporta grupos `\1`, `\2`… |
| Alterar caixa (upper/lower) | "Alterar caixa" | 4 modos + remover acentos |
| Remover caracteres | "Remover" ou "Substituir" por vazio | "Remover" é por intervalo |
| Inserir prefixo/sufixo | "Inserir" posição 1 ou reverso | Reverso = do fim |
| Aplicar a extensão apenas | Escopo "Extensão" | — |
| Aplicar ao nome apenas | Escopo "Nome" | — |
| Token EXIF `[exif:date]` | ❌ Não nativo | Extraia com `exiftool -d '%Y%m%d' -DateTimeOriginal -s3 *.jpg` e renomeie manualmente ou via script |
| Token ID3 `[mp3:artist]` | ❌ Não nativo | Use `id3v2 -l` ou `ffprobe`, depois insira via Bulky |
| Copiar arquivos durante renomeação | ❌ Não suportado | Bulky só renomeia; copie antes com `cp` |

### Fluxo Recomendado
1. **Para regras simples** (substituir/inserir/caixa/numeração): migre direto para Bulky; é mais rápido e intuitivo.
2. **Para regras com metadados** (EXIF/ID3): continue usando KRename ou extraia metadados com ferramentas CLI (`exiftool`, `ffprobe`) e incorpore ao nome via script + Bulky.
3. **Para perfis complexos com múltiplas etapas**: considere script shell/Python chamando operações do Bulky ou mantenha KRename.

---

## Roteiro de Migração: GPRename → Bulky

| Operação no GPRename | Equivalente no Bulky |
|----------------------|----------------------|
| Substituir texto | "Substituir" (literal ou regex) |
| Inserir no início | "Inserir" posição 1 |
| Inserir no fim | "Inserir" reverso posição 1 |
| Numeração | `%n` com início/incremento |
| Remover caracteres | "Remover" (de/até) ou "Substituir" por vazio |
| Upper/Lower case | "Alterar caixa" |

---

## Checklist de Decisão

### Use **Bulky** se você precisa:
- [ ] Interface limpa e moderna (XApp)
- [ ] Pré-visualização clara com validações automáticas
- [ ] Renomeação assíncrona para não travar em lotes grandes
- [ ] Operações comuns cobertas (substituir, inserir, remover, caixa, numeração)
- [ ] Integração com Cinnamon, MATE, GNOME
- [ ] Cache de thumbnails persistente
- [ ] Não depende de metadados EXIF/ID3

### Use **KRename** se você precisa:
- [ ] Tokens de metadados (EXIF, ID3/OGG, datas, tamanho, hash)
- [ ] Múltiplas regras encadeadas em um perfil
- [ ] Copiar/mover arquivos durante o processo
- [ ] Integração profunda com KDE/Plasma
- [ ] Plugins e extensibilidade
- [ ] Modo dry-run detalhado

### Use **GPRename** se você precisa:
- [ ] Ferramenta minimalista e leve
- [ ] Operações básicas sem complexidade
- [ ] Ambiente GTK com recursos limitados
- [ ] Renomeações rápidas sem pré-visualização rica

---

## Suporte e Contribuições

- **Bulky**: [linuxmint/bulky](https://github.com/linuxmint/bulky)
- **KRename**: [KDE KRename](https://kde.org/applications/utilities/org.kde.krename)
- **GPRename**: [GPRename SourceForge](http://gprename.sourceforge.net/)

Para bugs, melhorias ou traduções do Bulky, veja [DEVELOPMENT.md](DEVELOPMENT.md) e [CONTRIBUTING.md](https://github.com/linuxmint/bulky/blob/master/CONTRIBUTING.md) (se existir).

---

**Última atualização**: 2026-01-12  
**Versão testada**: Bulky (commit atual), KRename 5.x, GPRename 20230x
