# AVALIAÇÃO COMPLETA DO BULKY
## Auditoria GUI/UX + QA + Core Application

**Data**: 2026-01-12  
**Versão analisada**: Commit d97b42b (com ferramentas integradas)  
**Escopo**: Interface GTK3, Core Python, Fluxos E2E, Qualidade e Arquitetura

---

## A) RESUMO EXECUTIVO

### 🎯 Principais Achados

**GUI/UX (5 issues principais)**:
1. ⚠️ **Acessibilidade limitada**: Sem navegação por teclado completa, foco visual insuficiente, labels ARIA ausentes
2. ⚠️ **Estados incompletos**: Falta feedback visual durante operações longas (renaming), sem skeleton/placeholder
3. ℹ️ **Hierarquia visual confusa**: Botão "Rename" não destacado suficientemente como ação primária
4. ℹ️ **Responsividade**: Janela não se adapta bem a telas pequenas (< 800px width)
5. ℹ️ **Tooltips inconsistentes**: Alguns botões sem explicação hover

**QA e Robustez (5 issues principais)**:
1. 🔴 **Cobertura de testes baixa**: Apenas 14 testes unitários, zero testes de integração/e2e
2. 🔴 **Validação de entrada frágil**: Regex patterns não validados antes de compilação
3. ⚠️ **Concorrência**: Threads de thumbnail/rename sem sincronização adequada, potencial race condition
4. ⚠️ **Recuperação de erro**: Operações de rename falham sem rollback ou undo
5. ℹ️ **Observabilidade**: Logs não estruturados, sem correlação de operações

**Performance e Arquitetura (4 issues principais)**:
1. ℹ️ **Cache de regex**: Implementado mas sem métricas de hit rate
2. ℹ️ **Thumbnails**: Bom uso de cache persistente, mas sem limite de tamanho (pode crescer indefinidamente)
3. ℹ️ **Duplicação de código**: Lógica de diálogos repetida 4x nas ferramentas integradas
4. ℹ️ **Acoplamento**: FileObject conhece detalhes de UI (scale factor)

### 📊 Métricas Atuais vs. Alvos

| Métrica | Atual | Alvo | Gap |
|---------|-------|------|-----|
| **Cobertura de testes** | ~15% (estimado) | 70%+ | 🔴 55% |
| **Acessibilidade WCAG** | Nível ? (não testado) | A mínimo | 🔴 - |
| **Startup (GUI ready)** | ~781ms | < 500ms | ⚠️ 281ms |
| **Rename throughput** | ~48k files/s | Manter | ✅ OK |
| **RSS Memory (idle)** | 44 MB | < 50 MB | ✅ OK |

---

## B) ESCOPO ANALISADO E BASELINE

### Fontes Analisadas

```
usr/lib/bulky/bulky.py         (1486 linhas) ✅ Core application
usr/share/bulky/bulky.ui       (949 linhas)  ✅ GTK3 interface
tests/test_bulky.py            (14 testes)   ✅ Unit tests
migration_scripts/             (4 scripts)   ✅ CLI tools
.github/workflows/ci.yml                     ✅ CI pipeline
RELATORIO_FINAL.md                           ✅ Benchmarks
```

### Fluxos E2E Críticos Mapeados

1. **Adicionar arquivos** (Ctrl+N / Drag&Drop)
2. **Substituir texto** (com/sem regex)
3. **Renomear em lote** (operação assíncrona)
4. **Ferramentas avançadas** (EXIF/ID3/Hash/Normalize)
5. **Preview e validação** (colisões/permissões)

### Baseline de UX (medido)

- **Startup wall time**: 781ms (média de 3 runs)
- **Startup perceived**: 592ms (inline time to window)
- **Import time**: 23.64ms (média), 113.21ms (worst-case)
- **Rename per-file**: 0.021ms (~48k files/s)

### Não Verificado

- ❌ Testes de usabilidade com usuários reais
- ❌ Auditoria de acessibilidade automatizada (axe/pa11y)
- ❌ Testes de carga (> 10k arquivos)
- ❌ Testes de integração (Gio/GLib/GTK mocking)
- ❌ Métricas de produção (se existir telemetria)

---

## C) MAPA DO SISTEMA E FLUXOS CRÍTICOS

### Arquitetura de Componentes

```
┌─────────────────────────────────────────────────────┐
│                   MyApplication                     │
│              (Gtk.Application lifecycle)            │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │    MainWindow       │  ← Core UI controller
        │  - model (TreeStore)│
        │  - operation handlers│
        │  - tool integrations │
        └──────────┬──────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
┌────▼─────┐  ┌───▼────┐  ┌────▼─────┐
│FileObject│  │Preview │  │ Rename   │
│(Gio.File)│  │Engine  │  │ Engine   │
└──────────┘  └────────┘  └──────────┘
     │             │             │
     └─────────────┴─────────────┘
                   │
          ┌────────▼────────┐
          │  Async Workers  │
          │ - Thumbnails    │
          │ - Rename batch  │
          │ - Tool helpers  │
          └─────────────────┘
```

### Telas e Rotas (GTK Dialogs)

| Componente | Propósito | Estados | Acessibilidade |
|------------|-----------|---------|----------------|
| `main_window` | Janela principal | normal, busy | ⚠️ Parcial |
| `infobar` | Erros/avisos | hidden, error, warning | ⚠️ Sem ARIA |
| `treeview` | Lista de arquivos | empty, loading, populated | ❌ Sem estados |
| `combo_operation` | Tipo de operação | 4 opções | ✅ OK |
| `stack` | Painéis de opções | 4 pages | ✅ OK |
| Ferramentas (4) | Diálogos modais | OK/Cancel | ⚠️ Sem keyboard nav |

### Pontos de Fricção Identificados

1. **Add files**: Sem indicador de progresso em diretórios grandes
2. **Preview**: Não mostra diferença visual clara entre original/novo
3. **Rename**: Operação longa sem progress bar, apenas desabilita UI
4. **Errors**: Infobar aparece mas não auto-hide, acumula se múltiplos erros
5. **Tools**: Requerem múltiplos cliques, sem atalhos de teclado

---

## D) ACHADOS DETALHADOS

### 📱 D1. GUI/UX E ACESSIBILIDADE

#### D1.1 Navegação por Teclado Incompleta

**Evidência**: `bulky.ui` linhas 1-949  
**Impacto**: Usuários com deficiência motora ou preferência de teclado não conseguem usar completamente

**Problemas específicos**:
- TreeView não tem binding para Delete key (remover item)
- Botões de toolbar sem mnemonics (<kbd>Alt+A</kbd> para Add)
- Ferramentas do menu Tools sem accelerators
- Campos de entrada em diálogos sem tab order explícito

**Causa provável**: Foco em mouse/drag&drop, acessibilidade não priorizada

**Recomendação**:
```python
# Em MainWindow.__init__(), após conectar botões:
self.window.connect("key-press-event", self.on_global_key_press)

def on_global_key_press(self, widget, event):
    ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
    if event.keyval == Gdk.KEY_Delete:
        self.on_remove_button(None)
        return True
    if ctrl and event.keyval == Gdk.KEY_e:
        self.on_tool_exif_rename(None)
        return True
    # ... adicionar mais atalhos
```

**Validação**: Testar com <kbd>Tab</kbd>, <kbd>Shift+Tab</kbd>, <kbd>Enter</kbd>, <kbd>Delete</kbd>, <kbd>Ctrl+*</kbd> em todos os fluxos

---

#### D1.2 Foco Visual Insuficiente

**Evidência**: `bulky.ui` não define `:focus` styles customizados  
**Impacto**: Usuários com baixa visão ou usando teclado perdem contexto

**Problemas específicos**:
- TreeView rows não destacam claramente quando focused
- Botões apenas mudam cor de fundo (pode não ser suficiente)
- Entry fields sem borda destacada em foco

**Causa provável**: Dependência de temas GTK padrão

**Recomendação**:
```css
/* Criar usr/share/bulky/bulky.css */
treeview:focus row:selected {
    outline: 2px solid @theme_selected_bg_color;
    outline-offset: 2px;
}

button:focus {
    box-shadow: 0 0 0 2px @theme_selected_bg_color;
}

entry:focus {
    border-width: 2px;
    border-color: @theme_selected_bg_color;
}
```

```python
# Em MainWindow.__init__():
css_provider = Gtk.CssProvider()
css_provider.load_from_path("/usr/share/bulky/bulky.css")
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(),
    css_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)
```

**Validação**: Auditar com ferramentas de acessibilidade (Accessibility Inspector) e testar navegação por teclado

---

#### D1.3 Labels e Semântica ARIA Ausentes

**Evidência**: `bulky.ui` linhas 255-300 (botões de toolbar)  
**Impacto**: Leitores de tela não descrevem ações claramente

**Problemas específicos**:
```xml
<!-- ANTES: bulky.ui -->
<object class="GtkButton" id="add_button">
  <property name="image">add_icon</property>
  <property name="tooltip-text">Add files</property>
</object>

<!-- Problema: sem label explícito, apenas ícone + tooltip -->
```

**Causa provável**: Design icon-only para economia de espaço

**Recomendação**:
```xml
<!-- DEPOIS: bulky.ui -->
<object class="GtkButton" id="add_button">
  <property name="image">add_icon</property>
  <property name="tooltip-text" translatable="yes">Add files</property>
  <property name="label" translatable="yes">Add</property>
  <property name="always-show-image">True</property>
  <accessibility>
    <relation type="labelled-by" target="add_button_label"/>
  </accessibility>
</object>
```

**Validação**: Testar com Orca/NVDA e verificar que descreve "Add files button"

---

#### D1.4 Contraste de Cores Não Verificado

**Evidência**: Dependência de temas GTK sem validação WCAG  
**Impacto**: Usuários com baixa visão ou daltonismo podem ter dificuldade

**Problemas específicos**:
- Infobar error: tema pode não ter contraste 4.5:1
- TreeView selected: idem
- Disabled buttons: podem ficar invisíveis em temas claros

**Causa provável**: Confiança em temas do sistema

**Recomendação**:
```python
# Adicionar validação de contraste em MainWindow.__init__():
def ensure_min_contrast(fg_color, bg_color, min_ratio=4.5):
    """Verifica e ajusta contraste WCAG AA."""
    luminance_fg = calculate_relative_luminance(fg_color)
    luminance_bg = calculate_relative_luminance(bg_color)
    ratio = (max(luminance_fg, luminance_bg) + 0.05) / \
            (min(luminance_fg, luminance_bg) + 0.05)
    if ratio < min_ratio:
        # Ajustar fg_color para atingir min_ratio
        pass  # Implementar ajuste
    return fg_color

# Aplicar a cores críticas (error, selected, disabled)
```

**Validação**: Usar ferramenta como [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) em screenshots

---

#### D1.5 Estados de Loading Sem Feedback Visual

**Evidência**: `on_rename_button()` linha 707: `self.window.set_sensitive(False)`  
**Impacto**: Usuário não sabe se app travou ou está processando

**Problemas específicos**:
- Rename batch apenas desabilita janela (fica cinza)
- Sem progress bar ou contador
- Sem possibilidade de cancelar operação longa
- Thumbnails carregam silenciosamente (ok, mas sem indicador global)

**Causa provável**: Simplicidade de implementação inicial

**Recomendação**:
```python
# ANTES: on_rename_button()
self.rename_button.set_sensitive(False)
self.window.set_sensitive(False)

# DEPOIS: adicionar progress dialog
def on_rename_button(self, widget):
    # ... coleta rename_list ...
    
    progress_dialog = Gtk.Dialog(
        title=_("Renaming files..."),
        transient_for=self.window,
        modal=True
    )
    progress_bar = Gtk.ProgressBar()
    progress_bar.set_show_text(True)
    content = progress_dialog.get_content_area()
    content.add(progress_bar)
    progress_dialog.set_default_size(400, 100)
    progress_dialog.show_all()
    
    total = len(rename_list)
    processed = [0]  # mutable for closure
    
    def worker():
        for i, tup in enumerate(rename_list):
            # ... rename logic ...
            processed[0] = i + 1
            GLib.idle_add(lambda: progress_bar.set_fraction(processed[0] / total))
            GLib.idle_add(lambda: progress_bar.set_text(f"{processed[0]}/{total}"))
        GLib.idle_add(progress_dialog.destroy)
    
    threading.Thread(target=worker, daemon=True).start()
```

**Validação**: Renomear 100+ arquivos e verificar que progress bar atualiza suavemente

---

#### D1.6 Hierarquia Visual Confusa

**Evidência**: `bulky.ui` linhas 150-200 (headerbar buttons)  
**Impacto**: Botão "Rename" (ação primária) não se destaca

**Problemas específicos**:
- Todos os botões têm mesmo peso visual
- "Rename" deveria ser destaque (suggested-action style)
- "Clear" poderia ser destrutivo (destructive-action style)

**Causa provável**: Design padrão GTK sem customização

**Recomendação**:
```xml
<!-- bulky.ui: adicionar style classes -->
<object class="GtkButton" id="rename_button">
  <property name="label" translatable="yes">Rename</property>
  <style>
    <class name="suggested-action"/>
  </style>
</object>

<object class="GtkButton" id="clear_button">
  <property name="label" translatable="yes">Clear</property>
  <style>
    <class name="destructive-action"/>
  </style>
</object>
```

**Validação**: Visual inspection — "Rename" deve aparecer em azul/verde, "Clear" em vermelho

---

### 🧪 D2. QUALIDADE E TESTES

#### D2.1 Cobertura de Testes Crítica

**Evidência**: `tests/test_bulky.py` — apenas 14 testes unitários  
**Impacto**: Alta probabilidade de regressões não detectadas

**Lacunas principais**:
```
Tipo de Teste         | Atual | Recomendado | Gap
--------------------- | ----- | ----------- | -----
Unit (funções)        | 14    | 50+         | 🔴 36+
Integration (Gio)     | 0     | 20+         | 🔴 20+
E2E (GUI + fluxo)     | 0     | 10+         | 🔴 10+
Regression            | 0     | 5+          | 🔴 5+
Performance           | 2     | 5+          | ⚠️ 3+
```

**Fluxos sem cobertura**:
- ❌ Drag & drop de arquivos
- ❌ Renomeação com colisões
- ❌ Ferramentas (EXIF/ID3/Hash/Normalize)
- ❌ Undo/cancelamento
- ❌ Recuperação de erro durante rename

**Causa provável**: Foco em funcionalidade sobre testes

**Recomendação**: Criar `tests/test_integration.py`
```python
import unittest
from unittest.mock import Mock, patch
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio

class TestBulkyIntegration(unittest.TestCase):
    def setUp(self):
        self.app = MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        self.window = MainWindow(self.app)
    
    def test_add_file_updates_model(self):
        """Adicionar arquivo deve popular TreeStore."""
        initial_count = len(self.window.model)
        self.window.add_file("/tmp/test.txt")
        self.assertEqual(len(self.window.model), initial_count + 1)
    
    def test_rename_with_collision_shows_error(self):
        """Colisão de nomes deve exibir infobar."""
        # Setup: 2 arquivos que vão colidir
        self.window.add_file("/tmp/file1.txt")
        self.window.add_file("/tmp/file2.txt")
        # ... configurar substituição que causa colisão ...
        self.window.preview_changes()
        self.assertTrue(self.window.infobar.get_visible())
    
    # ... adicionar 20+ testes de integração
```

**Validação**: `make test` deve executar > 80 testes com > 70% de cobertura

---

#### D2.2 Validação de Entrada Frágil

**Evidência**: `replace_text()` linha 881 — regex não validado  
**Impacto**: Usuário pode travar app com regex mal-formado

**Problemas específicos**:
```python
# ANTES: _compile_regex()
@functools.lru_cache(maxsize=32)
def _compile_regex(self, pattern, flags):
    """Cache compiled regex patterns to avoid recompilation."""
    return re.compile(pattern, flags)  # ← Pode lançar re.error

# Chamado em replace_text() sem try/except
reg = self._compile_regex(find, flags)
return reg.sub(replace, string)
```

**Causa provável**: Confiança em `try/except` externo genérico

**Recomendação**:
```python
# DEPOIS: validação antecipada
def _compile_regex(self, pattern, flags):
    try:
        compiled = re.compile(pattern, flags)
        return compiled
    except re.error as e:
        logger.warning(f"Invalid regex '{pattern}': {e}")
        raise ValueError(f"Invalid regular expression: {e}")

# Em replace_text():
try:
    reg = self._compile_regex(find, flags)
    return reg.sub(replace, string)
except ValueError as e:
    # Mostrar erro no infobar
    GLib.idle_add(lambda: self.infobar.show())
    GLib.idle_add(lambda: self.error_label.set_text(str(e)))
    return string  # Não aplica substituição
```

**Validação**: Testar com regex inválidos: `[unclosed`, `(?P<name)`, `*invalid`

---

#### D2.3 Concorrência Sem Sincronização

**Evidência**: `_load_thumbnail_async()` linha 530 + `on_rename_button()` linha 707  
**Impacto**: Race conditions, potencial corrupção de `self.model`

**Problemas específicos**:
- `_load_thumbnail_async` cria threads que atualizam `self.model` via `GLib.idle_add`
- `on_rename_button` cria thread que também atualiza `self.model`
- Se ambas rodarem simultaneamente, podem sobrescrever mudanças uma da outra
- `self._thumb_pending` (set) não é thread-safe em Python < 3.11

**Causa provável**: Otimismo em GLib.idle_add como sincronização suficiente

**Recomendação**:
```python
import threading

class MainWindow():
    def __init__(self, application):
        # ... existing code ...
        self._model_lock = threading.Lock()
    
    def _load_thumbnail_async(self, iter_, file_obj):
        def worker():
            # ... load pixbuf ...
            def apply_pix():
                with self._model_lock:  # ← Proteger acesso ao model
                    try:
                        if pix is not None:
                            self.model.set_value(iter_, COL_PIXBUF, pix)
                        self._thumb_pending.discard(file_obj.uri)
                    except Exception:
                        pass
                return False
            GLib.idle_add(apply_pix)
        threading.Thread(target=worker, daemon=True).start()
    
    def on_rename_button(self, widget):
        def worker():
            for tup in rename_list:
                # ... rename ...
                def apply_update():
                    with self._model_lock:  # ← Proteger acesso ao model
                        # ... update model ...
                        pass
                    return False
                GLib.idle_add(apply_update)
        threading.Thread(target=worker, daemon=True).start()
```

**Validação**: Stress test — adicionar 1000 imagens e renomear imediatamente

---

#### D2.4 Operações Sem Rollback/Undo

**Evidência**: `on_rename_button()` linha 683 — rename pode falhar parcialmente  
**Impacto**: Usuário pode ficar com arquivos parcialmente renomeados

**Problemas específicos**:
```python
# ANTES: on_rename_button worker
for tup in rename_list:
    # ... rename file_obj ...
    if success:
        # atualiza model
    # ← Se falhar aqui, já renomeou alguns arquivos sem como reverter
```

**Causa provável**: Operação FS é atomic per-file, mas não há transação global

**Recomendação**:
```python
def on_rename_button(self, widget):
    # ... build rename_list ...
    
    # Armazenar backup log antes de começar
    backup_log = []
    for it, file_obj, old_name, new_name in rename_list:
        backup_log.append((file_obj.uri, old_name))
    
    self._last_rename_backup = backup_log
    self._last_rename_success = []
    
    def worker():
        for tup in rename_list:
            it, file_obj, name, new_name = tup
            if new_name != name:
                try:
                    old_uri = file_obj.uri
                    success = file_obj.rename(new_name)
                    if success:
                        self._last_rename_success.append((old_uri, file_obj.uri))
                        # ... update model ...
                except GLib.Error as e:
                    # Oferecer rollback
                    def offer_rollback():
                        dialog = Gtk.MessageDialog(...)
                        dialog.format_secondary_text(
                            _("Rename failed. Roll back changes?")
                        )
                        if dialog.run() == Gtk.ResponseType.YES:
                            self.rollback_last_rename()
                        dialog.destroy()
                    GLib.idle_add(offer_rollback)
                    break
        # ... done ...
    threading.Thread(target=worker, daemon=True).start()

def rollback_last_rename(self):
    """Reverte última operação de rename."""
    for (new_uri, old_name) in reversed(self._last_rename_success):
        file = Gio.File.new_for_uri(new_uri)
        try:
            file.set_display_name(old_name, None)
        except Exception as e:
            logger.error(f"Rollback failed for {new_uri}: {e}")
```

**Validação**: Forçar falha no meio de um batch e verificar que rollback funciona

---

### ⚡ D3. PERFORMANCE E EFICIÊNCIA

#### D3.1 Cache de Regex Sem Métricas

**Evidência**: `_compile_regex()` linha 870 usa `@lru_cache`  
**Impacto**: Não sabemos se está sendo efetivo

**Problema**: Sem instrumentação, não podemos validar que:
- Padrões estão sendo reutilizados
- Tamanho do cache (32) é adequado
- Hit rate justifica overhead

**Recomendação**:
```python
import functools
from collections import defaultdict

class MainWindow():
    def __init__(self, application):
        # ... existing code ...
        self._regex_cache_stats = defaultdict(int)
    
    @functools.lru_cache(maxsize=32)
    def _compile_regex(self, pattern, flags):
        """Cache compiled regex patterns to avoid recompilation."""
        self._regex_cache_stats['compiles'] += 1
        return re.compile(pattern, flags)
    
    def get_regex_cache_stats(self):
        info = self._compile_regex.cache_info()
        hit_rate = info.hits / (info.hits + info.misses) if (info.hits + info.misses) > 0 else 0
        return {
            'hits': info.hits,
            'misses': info.misses,
            'hit_rate': hit_rate,
            'size': info.currsize,
            'maxsize': info.maxsize
        }
    
    # Logar stats ao fechar ou no About
    def on_menu_quit(self, widget):
        if ENABLE_TELEMETRY:
            stats = self.get_regex_cache_stats()
            logger.info(f"Regex cache stats: {stats}")
        self.application.quit()
```

**Validação**: Habilitar telemetria, fazer 10 substituições com mesmo padrão, verificar logs

---

#### D3.2 Cache de Thumbnails Sem Limite

**Evidência**: `_thumb_cache_dir` linha 238, salva PNGs indefinidamente  
**Impacto**: Pode crescer até GB com uso prolongado

**Problema**:
```python
# ANTES: sem limpeza
self._thumb_cache_dir = Path(os.path.expanduser("~/.cache/bulky/thumbnails"))
self._thumb_cache_dir.mkdir(parents=True, exist_ok=True)
# ← Cache cresce indefinidamente
```

**Recomendação**:
```python
def __init__(self, application):
    # ... existing code ...
    self._thumb_cache_dir = Path(os.path.expanduser("~/.cache/bulky/thumbnails"))
    self._thumb_cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Limpar cache antigo no startup
    self._cleanup_old_thumbnails()

def _cleanup_old_thumbnails(self, max_age_days=30, max_size_mb=100):
    """Remove thumbnails antigos ou se cache > max_size."""
    import time
    
    try:
        cache_size = sum(f.stat().st_size for f in self._thumb_cache_dir.glob('*.png'))
        cache_size_mb = cache_size / (1024 * 1024)
        
        if cache_size_mb > max_size_mb:
            logger.info(f"Thumbnail cache is {cache_size_mb:.1f}MB, cleaning...")
            # Remover arquivos mais antigos primeiro
            files = sorted(
                self._thumb_cache_dir.glob('*.png'),
                key=lambda f: f.stat().st_mtime
            )
            for f in files[:len(files)//2]:  # Remove metade dos mais antigos
                f.unlink()
        
        # Remover thumbnails > max_age_days
        cutoff = time.time() - (max_age_days * 86400)
        for f in self._thumb_cache_dir.glob('*.png'):
            if f.stat().st_mtime < cutoff:
                f.unlink()
    except Exception as e:
        logger.warning(f"Failed to cleanup thumbnails: {e}")
```

**Validação**: Popular cache com 200+ thumbnails, reiniciar app, verificar que cache < 100MB

---

### 🏗️ D4. ARQUITETURA E MANUTENIBILIDADE

#### D4.1 Duplicação de Código em Ferramentas

**Evidência**: `on_tool_*()` métodos (linhas 592-908) repetem estrutura de diálogo  
**Impacto**: Manutenção custosa, inconsistência entre ferramentas

**Problema**:
```python
# 4x repetido:
dialog = Gtk.Dialog(title=_("..."), transient_for=self.window, flags=0)
dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                   Gtk.STOCK_OK, Gtk.ResponseType.OK)
box = dialog.get_content_area()
box.set_spacing(6)
box.set_margin_top(12)
# ... etc
response = dialog.run()
dialog.destroy()
```

**Recomendação**:
```python
def _create_tool_dialog(self, title, widgets, width=400, height=200):
    """Factory para diálogos de ferramentas."""
    dialog = Gtk.Dialog(
        title=title,
        transient_for=self.window,
        flags=0
    )
    dialog.add_buttons(
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
        Gtk.STOCK_OK, Gtk.ResponseType.OK
    )
    dialog.set_default_size(width, height)
    
    box = dialog.get_content_area()
    box.set_spacing(6)
    for prop in ['margin_top', 'margin_bottom', 'margin_start', 'margin_end']:
        setattr(box, prop, 12)
    
    for widget in widgets:
        box.pack_start(widget, False, False, 6)
    
    box.show_all()
    return dialog

# Uso:
def on_tool_exif_rename(self, widget):
    prefix_entry = Gtk.Entry()
    # ... setup widget ...
    
    widgets = [
        Gtk.Label(label=_("Format: YYYYMMDD_HHMMSS_NNN.ext")),
        self._create_labeled_entry(_("Prefix:"), prefix_entry),
        Gtk.Label(markup=_("<small>Only JPEG files...</small>"))
    ]
    
    dialog = self._create_tool_dialog(_("Rename by EXIF Date"), widgets)
    response = dialog.run()
    prefix = prefix_entry.get_text()
    dialog.destroy()
    # ... rest
```

**Validação**: Refatorar e garantir que todos os 4 diálogos continuam funcionando

---

#### D4.2 FileObject Acoplado com UI

**Evidência**: `FileObject.__init__()` linha 94 recebe `scale` (fator de escala da janela)  
**Impacto**: Objeto de domínio conhece detalhes de apresentação

**Problema**:
```python
class FileObject():
    def __init__(self, path_or_uri, scale):  # ← scale é detalhe de UI
        self.scale = scale
```

**Causa**: Thumbnails precisam do scale para rendering

**Recomendação**:
```python
# DEPOIS: separar responsabilidades
class FileObject():
    def __init__(self, path_or_uri):
        self.gfile = self.create_gfile(path_or_uri)
        self._update_info()
        # Sem 'scale'

# Em MainWindow:
def _get_thumbnail_for_file(self, file_obj):
    """Retorna pixbuf com scale correto."""
    scale = self.window.get_scale_factor()
    # ... lógica de thumbnail usando scale localmente
```

**Validação**: Refatorar e garantir que thumbnails ainda renderizam corretamente

---

## E) AÇÕES E MELHORIAS PROPOSTAS

### E1. Quick Wins de GUI/UX (Onda 1)

#### E1.1 Adicionar Atalhos de Teclado

**Objetivo**: Melhorar acessibilidade e produtividade

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (MainWindow.__init__)

**Mudança**:
```python
# Adicionar em MainWindow.__init__(), após setup de menu:
accel_group = Gtk.AccelGroup()
self.window.add_accel_group(accel_group)

# Atalhos principais
shortcuts = [
    ('<Control>n', self.on_add_button),
    ('<Control>d', self.on_remove_button),
    ('<Control>r', self.on_rename_button),
    ('Delete', self.on_remove_button),
    ('<Control>e', self.on_tool_exif_rename),
    ('<Control>i', self.on_tool_id3_rename),
    ('<Control>h', self.on_tool_hash_rename),
    ('<Control>l', self.on_tool_normalize),  # L de "clean/limpar"
]

for accel, handler in shortcuts:
    key, mod = Gtk.accelerator_parse(accel)
    accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                       lambda *args, h=handler: h(None) or True)
```

**Validação**:
- [ ] Pressionar <kbd>Ctrl+N</kbd> abre diálogo de adicionar
- [ ] Pressionar <kbd>Delete</kbd> remove item selecionado
- [ ] Todos os 7 atalhos funcionam

**Risco**: Baixo (não altera funcionalidade)

---

#### E1.2 Adicionar Progress Bar em Rename

**Objetivo**: Feedback visual durante operações longas

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (on_rename_button)

**Mudança**: Ver seção D1.5 acima

**Validação**:
- [ ] Progress bar aparece ao renomear > 10 arquivos
- [ ] Texto atualiza "X/Y"
- [ ] Dialog fecha automaticamente ao terminar
- [ ] Usuário pode cancelar (futuro)

**Risco**: Médio (altera fluxo de rename, testar bem)

---

### E2. Robustez e Qualidade (Onda 2)

#### E2.1 Criar Suite de Testes de Integração

**Objetivo**: Aumentar cobertura de 15% → 70%+

**Arquivos afetados**:
- `tests/test_integration.py` (novo)
- `tests/test_e2e_gui.py` (novo)
- `.github/workflows/ci.yml`

**Mudança**: Ver seção D2.1 acima

**Critérios de aceite**:
- [ ] 20+ testes de integração (Gio/GLib mocking)
- [ ] 10+ testes E2E (fluxos completos)
- [ ] Cobertura > 70% em `bulky.py`
- [ ] CI roda todos os testes em < 5min

**Esforço**: Grande (2-3 semanas)  
**Risco**: Baixo (adiciona testes, não muda código)

---

#### E2.2 Adicionar Validação de Regex

**Objetivo**: Prevenir crash com regex inválido

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (_compile_regex, replace_text)

**Mudança**: Ver seção D2.2 acima

**Validação**:
- [ ] Testar com `[unclosed` → mostra erro no infobar
- [ ] Testar com `(?P<incomplete` → idem
- [ ] App não trava com qualquer regex

**Esforço**: Pequeno (2-4 horas)  
**Risco**: Baixo

---

#### E2.3 Adicionar Locks de Concorrência

**Objetivo**: Prevenir race conditions

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (MainWindow, _load_thumbnail_async, on_rename_button)

**Mudança**: Ver seção D2.3 acima

**Validação**:
- [ ] Stress test: 1000 imagens + rename imediato
- [ ] Não há crashes ou corrupção de model
- [ ] Performance não regride > 10%

**Esforço**: Médio (1-2 dias)  
**Risco**: Médio (altera concorrência)

---

#### E2.4 Implementar Rollback de Rename

**Objetivo**: Recuperação de erros graceful

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (on_rename_button, novo método rollback_last_rename)

**Mudança**: Ver seção D2.4 acima

**Validação**:
- [ ] Forçar falha no meio de batch
- [ ] Dialog oferece rollback
- [ ] Rollback reverte arquivos renomeados
- [ ] Model fica consistente

**Esforço**: Médio (2-3 dias)  
**Risco**: Alto (operação FS complexa)

---

### E3. Instrumentação e Performance (Onda 3)

#### E3.1 Adicionar Métricas de Regex Cache

**Objetivo**: Validar eficácia do cache

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (_compile_regex, on_menu_quit)

**Mudança**: Ver seção D3.1 acima

**Validação**:
- [ ] Habilitar `BULKY_TELEMETRY=1`
- [ ] Fazer 10 substituições com mesmo padrão
- [ ] Ver no log: hit_rate > 80%

**Esforço**: Pequeno (1-2 horas)  
**Risco**: Baixo

---

#### E3.2 Implementar Limpeza de Cache de Thumbnails

**Objetivo**: Prevenir crescimento descontrolado

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (__init__, _cleanup_old_thumbnails)

**Mudança**: Ver seção D3.2 acima

**Validação**:
- [ ] Popular cache com 500+ thumbs
- [ ] Reiniciar app
- [ ] Cache reduzido para < 100MB

**Esforço**: Pequeno (2-3 horas)  
**Risco**: Baixo

---

### E4. Refatoração Estrutural (Onda 4)

#### E4.1 Extrair Factory de Diálogos

**Objetivo**: Reduzir duplicação, facilitar manutenção

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (todos os on_tool_*, novo _create_tool_dialog)

**Mudança**: Ver seção D4.1 acima

**Validação**:
- [ ] Refatorar 4 ferramentas
- [ ] Todas continuam funcionando
- [ ] Código reduzido em ~150 linhas

**Esforço**: Médio (1 dia)  
**Risco**: Baixo (refactor isolado)

---

#### E4.2 Desacoplar FileObject de UI

**Objetivo**: Melhor separação de responsabilidades

**Arquivos afetados**:
- `usr/lib/bulky/bulky.py` (FileObject, MainWindow._get_thumbnail_for_file)

**Mudança**: Ver seção D4.2 acima

**Validação**:
- [ ] Thumbnails renderizam corretamente
- [ ] Testes unitários de FileObject não dependem de GTK

**Esforço**: Médio (1 dia)  
**Risco**: Médio (altera API interna)

---

## F) ROADMAP INCREMENTAL

### 🚀 Onda 1: Quick Wins (1 semana)

**Objetivo**: Melhorias de UX imediatas sem risco

| Tarefa | Esforço | Risco | Impacto |
|--------|---------|-------|---------|
| E1.1 Atalhos de teclado | 4h | Baixo | Alto |
| E1.2 Progress bar rename | 1d | Médio | Alto |
| E3.1 Métricas regex cache | 2h | Baixo | Médio |
| E3.2 Limpeza cache thumbs | 3h | Baixo | Médio |

**Critérios de sucesso**:
- ✅ Usuários podem usar app sem mouse
- ✅ Operações longas têm feedback visual
- ✅ Cache não cresce indefinidamente

**Rollback**: Git revert simples

---

### 🛡️ Onda 2: Robustez (2-3 semanas)

**Objetivo**: Aumentar confiabilidade e cobertura de testes

| Tarefa | Esforço | Risco | Impacto |
|--------|---------|-------|---------|
| E2.1 Testes integração | 3sem | Baixo | Alto |
| E2.2 Validação regex | 4h | Baixo | Alto |
| E2.3 Locks concorrência | 2d | Médio | Alto |
| E2.4 Rollback rename | 3d | Alto | Alto |

**Dependências**:
- E2.3 deve vir antes de E2.4 (rollback depende de locks)

**Critérios de sucesso**:
- ✅ Cobertura de testes > 70%
- ✅ Zero crashes com regex inválido
- ✅ Zero race conditions detectadas em stress test
- ✅ Usuário pode reverter rename parcial

**Rollback**: Feature flags para desabilitar novas funcionalidades

---

### 🎨 Onda 3: Acessibilidade (1-2 semanas)

**Objetivo**: WCAG AA compliance

| Tarefa | Esforço | Risco | Impacto |
|--------|---------|-------|---------|
| D1.2 Foco visual | 1d | Baixo | Alto |
| D1.3 Labels ARIA | 2d | Baixo | Alto |
| D1.4 Contraste cores | 1d | Baixo | Médio |
| Auditoria a11y | 1d | Baixo | - |

**Critérios de sucesso**:
- ✅ Passa em auditoria axe/pa11y com zero erros críticos
- ✅ Navegação completa por teclado em todos os fluxos
- ✅ Leitores de tela descrevem todas as ações

---

### 🏗️ Onda 4: Maturidade (1-2 semanas)

**Objetivo**: Reduzir débito técnico

| Tarefa | Esforço | Risco | Impacto |
|--------|---------|-------|---------|
| E4.1 Factory diálogos | 1d | Baixo | Médio |
| E4.2 Desacoplar FileObject | 1d | Médio | Médio |
| Design System básico | 2d | Baixo | Médio |

**Critérios de sucesso**:
- ✅ Duplicação de código < 5%
- ✅ Componentes reutilizáveis documentados
- ✅ Arquitetura limpa validada em code review

---

## G) BACKLOG EXECUTÁVEL

### Alta Prioridade (Próximos 7 dias)

#### G1. Adicionar atalhos de teclado
- **ID**: UX-001
- **Severidade**: Média
- **Impacto**: Usuário (produtividade)
- **Esforço**: Pequeno (4h)
- **Risco**: Baixo
- **Onda**: 1
- **Critérios**:
  - [ ] 7 atalhos implementados (Ctrl+N/D/R/E/I/H/L, Delete)
  - [ ] Documentados em Help/About
  - [ ] Testados manualmente

---

#### G2. Progress bar em rename
- **ID**: UX-002
- **Severidade**: Média
- **Impacto**: Usuário (percepção)
- **Esforço**: Médio (1d)
- **Risco**: Médio
- **Onda**: 1
- **Critérios**:
  - [ ] Dialog com progress bar aparece para > 10 arquivos
  - [ ] Texto atualiza "X/Y files"
  - [ ] Dialog fecha automaticamente
  - [ ] Sem regressão em performance de rename

---

#### G3. Validação de regex
- **ID**: ROBUST-001
- **Severidade**: Alta
- **Impacto**: Segurança (crash prevention)
- **Esforço**: Pequeno (4h)
- **Risco**: Baixo
- **Onda**: 2
- **Critérios**:
  - [ ] _compile_regex valida padrão antes de compilar
  - [ ] Erro mostrado no infobar
  - [ ] 3 regex inválidos testados (unclosed, incomplete, star)

---

### Média Prioridade (1-3 semanas)

#### G4. Locks de concorrência
- **ID**: ROBUST-002
- **Severidade**: Alta
- **Impacto**: Segurança (race conditions)
- **Esforço**: Médio (2d)
- **Risco**: Médio
- **Onda**: 2
- **Dependências**: Nenhuma
- **Critérios**:
  - [ ] threading.Lock protege acessos a self.model
  - [ ] Stress test com 1000 imagens + rename imediato
  - [ ] Zero crashes ou corrupção detectada

---

#### G5. Suite de testes de integração
- **ID**: QA-001
- **Severidade**: Alta
- **Impacto**: Qualidade (cobertura)
- **Esforço**: Grande (3sem)
- **Risco**: Baixo
- **Onda**: 2
- **Critérios**:
  - [ ] 20+ testes de integração
  - [ ] 10+ testes E2E
  - [ ] Cobertura > 70%
  - [ ] CI executa todos em < 5min

---

#### G6. Rollback de rename
- **ID**: ROBUST-003
- **Severidade**: Média
- **Impacto**: Usuário (recuperação de erro)
- **Esforço**: Médio (3d)
- **Risco**: Alto
- **Onda**: 2
- **Dependências**: G4 (locks)
- **Critérios**:
  - [ ] Backup log criado antes de rename
  - [ ] Dialog oferece rollback em caso de erro
  - [ ] Rollback reverte arquivos parciais
  - [ ] Model consistente após rollback

---

### Baixa Prioridade (Estrutural)

#### G7. Factory de diálogos
- **ID**: ARCH-001
- **Severidade**: Baixa
- **Impacto**: Manutenibilidade
- **Esforço**: Médio (1d)
- **Risco**: Baixo
- **Onda**: 4
- **Critérios**:
  - [ ] _create_tool_dialog() extrai lógica comum
  - [ ] 4 ferramentas refatoradas
  - [ ] ~150 linhas removidas
  - [ ] Todas as ferramentas continuam funcionando

---

## H) INSTRUMENTAÇÃO E VALIDAÇÃO

### H1. Métricas de Usabilidade

| Métrica | Baseline | Alvo | Como Medir |
|---------|----------|------|------------|
| **Tempo para primeira renomeação** | ~15s (estim.) | < 10s | Cronômetro manual |
| **Cliques para rename simples** | 5 | 3 | Contagem manual |
| **Taxa de erro (regex inválido)** | ? | < 5% | Logs + telemetria |
| **Uso de atalhos** | 0% | > 30% | Telemetria (futuro) |

### H2. Checklists de Acessibilidade

#### Navegação por Teclado
- [ ] Tab percorre todos os controles interativos
- [ ] Shift+Tab volta na ordem inversa
- [ ] Enter ativa botão com foco
- [ ] Esc fecha diálogos
- [ ] Delete remove item selecionado
- [ ] Atalhos Ctrl+* funcionam

#### Foco Visual
- [ ] Foco sempre visível (outline ou box-shadow)
- [ ] Contraste de foco > 3:1 com fundo
- [ ] TreeView row com foco destacado

#### Leitores de Tela
- [ ] Botões têm labels descritivos
- [ ] Ícones têm texto alternativo
- [ ] Mensagens de erro são anunciadas
- [ ] Progress bar anuncia progresso

### H3. Testes de Regressão

#### Suite Manual (executar antes de cada release)
1. **Adicionar arquivos**:
   - [ ] Via botão Add
   - [ ] Via Ctrl+N
   - [ ] Via Drag & Drop
   - [ ] Via argumentos CLI

2. **Operações de rename**:
   - [ ] Substituir texto simples
   - [ ] Substituir com regex
   - [ ] Inserir texto/contador
   - [ ] Remover caracteres
   - [ ] Alterar caixa
   - [ ] Remover acentos

3. **Ferramentas avançadas**:
   - [ ] EXIF rename (com/sem Pillow)
   - [ ] ID3 rename (com/sem ffmpeg)
   - [ ] Hash rename (SHA256/MD5)
   - [ ] Normalize names

4. **Validações**:
   - [ ] Colisão de nomes detectada
   - [ ] Permissões verificadas
   - [ ] Erros mostrados no infobar

5. **Performance**:
   - [ ] 100 arquivos renomeados em < 5s
   - [ ] Thumbnails carregam sem travar UI
   - [ ] Startup < 1s

---

## I) CHECKLIST FINAL DE QA

### Antes de Release

#### Funcionalidade Core
- [ ] Todos os fluxos E2E passam em teste manual
- [ ] Estados completos (loading/error/empty/success) implementados
- [ ] Sem regressões em funcionalidades existentes

#### Acessibilidade
- [ ] Navegação por teclado completa
- [ ] Foco visual em todos os controles
- [ ] Labels/ARIA em elementos interativos
- [ ] Contraste mínimo 4.5:1 validado
- [ ] Auditoria axe/pa11y sem erros críticos

#### Robustez
- [ ] Timeouts em operações I/O
- [ ] Validação de entrada em regex/paths
- [ ] Locks protegendo acesso concorrente
- [ ] Rollback implementado para operações críticas
- [ ] Logs estruturados em pontos-chave

#### Performance
- [ ] Startup < 1s
- [ ] Rename throughput > 40k files/s
- [ ] Memória < 50MB idle
- [ ] Cache de regex hit rate > 70%
- [ ] Cache de thumbnails < 100MB

#### Qualidade
- [ ] Cobertura de testes > 70%
- [ ] CI passa em todos os stages
- [ ] Linting sem warnings críticos
- [ ] Docs atualizadas (README, DEVELOPMENT)

#### Observabilidade
- [ ] Logs informativos (não debug em prod)
- [ ] Métricas de cache instrumentadas
- [ ] Telemetria respeitando privacidade

---

## J) RECOMENDAÇÕES FINAIS

### Priorização Sugerida

**Implementar imediatamente** (Quick Wins):
1. ✅ **G1**: Atalhos de teclado — impacto alto, risco baixo
2. ✅ **G3**: Validação de regex — previne crashes, esforço pequeno
3. ✅ **E3.2**: Limpeza de cache — previne crescimento descontrolado

**Próximas 2 semanas** (Robustez):
4. ✅ **G4**: Locks de concorrência — crítico para estabilidade
5. ✅ **G5**: Testes de integração — aumenta confiança
6. ✅ **G2**: Progress bar — melhora percepção de UX

**Médio prazo** (Acessibilidade):
7. ✅ **D1.2-D1.4**: Foco visual, ARIA, contraste
8. ✅ Auditoria completa de a11y

**Longo prazo** (Maturidade):
9. ✅ **G7**: Refatoração de diálogos
10. ✅ Design System básico

### Decisões de Trade-off

**Acessibilidade vs. Esforço**:
- **Decisão**: Priorizar navegação por teclado (alto impacto) sobre contraste automático (complexo)
- **Justificativa**: Mais usuários beneficiados com menos esforço

**Testes vs. Features**:
- **Decisão**: Pausar novas features até atingir 70% de cobertura
- **Justificativa**: Estabilidade atual é boa, mas base de testes frágil aumenta risco futuro

**Performance vs. UX**:
- **Decisão**: Adicionar progress bar mesmo com overhead de ~5%
- **Justificativa**: Percepção de responsividade > velocidade absoluta

### Riscos Residuais

Após implementar todo o roadmap, riscos remanescentes:

1. **Gio/GLib edge cases**: Hard de testar sem mocking sofisticado
2. **Performance em redes lentas**: Remote files via GVFS não otimizado
3. **Temas GTK exóticos**: Pode quebrar contraste/foco visual
4. **Thumbnails grandes**: JPEGs > 10MB podem travar thumb generation

**Mitigação**:
- Documentar limitações conhecidas
- Adicionar timeouts generosos em I/O remoto
- Testar com temas populares (Adwaita, Arc, Papirus)
- Limitar tamanho de arquivo para thumbnail (5MB)

---

## K) MÉTRICAS DE SUCESSO (3 MESES)

| KPI | Baseline | Alvo | Como Medir |
|-----|----------|------|------------|
| **WCAG Compliance** | Nível ? | AA | Auditoria axe |
| **Cobertura de Testes** | 15% | 70%+ | Coverage.py |
| **Bugs Críticos** | 0 (conhecidos) | 0 | Issue tracker |
| **Tempo de Startup** | 781ms | < 500ms | Benchmark |
| **Hit Rate Regex** | ? | > 70% | Telemetria |
| **Tamanho Cache Thumbs** | Ilimitado | < 100MB | Instrumentação |
| **Usuários de Atalhos** | 0% | > 30% | Telemetria (opt-in) |

---

**Conclusão**: O Bulky está em excelente estado funcional, com boa arquitetura base. Os principais gaps são em **acessibilidade**, **testes** e **feedback visual**. O roadmap proposto é incremental, de baixo risco e alto impacto. Priorizar Onda 1 e 2 trará benefícios imediatos sem comprometer estabilidade.
