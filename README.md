# 🏗️ Gestor de Obras

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?style=flat&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=flat&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Funcional-green)

Um aplicativo Desktop completo para **Gestores de Obra**. Desenvolvido para facilitar o controle diário de canteiros de obras, unificando gestão de pessoas, materiais, financeiro e diário de obra em uma única interface intuitiva.

---

## 🚀 Funcionalidades

### 📊 Visão Geral (Dashboard)
* **Cards de Resumo:** Saldo financeiro atual, funcionários presentes no dia e clima.
* **Alertas Inteligentes:** Aviso visual de materiais com estoque baixo (< 5 unidades).

### 👷 Gestão de Equipe
* **Cadastro Completo:** Dados pessoais, função (Pedreiro, Ajudante, etc.), dados bancários e admissão.
* **Controle de Presença:** Marcação de ponto por turnos (**Manhã** e **Tarde**), permitindo contabilizar meio dia de trabalho.
* **Gerenciamento de Inativos:** Histórico de funcionários dispensados com opção de reativação.

### 📦 Controle de Estoque
* **Movimentações:** Registro de entrada e saída de materiais com origem e destino.
* **Categorias:** Organização por Elétrica, Hidráulica, Alvenaria, etc.
* **Filtros Avançados:** Busca por item, fornecedor/origem ou categoria.
* **Exportação:** Gere planilhas `.csv` do saldo atual e do histórico completo.

### 💰 Financeiro (Caixinha)
* **Fluxo de Caixa:** Registro de pequenas despesas e entradas de recursos.
* **Nota Fiscal:** Campo dedicado para registrar número de NFs.
* **Saldo em Tempo Real:** Visualização colorida (Verde/Vermelho) do saldo.
* **Exportação:** Extrato financeiro exportável para CSV.

### 📘 Diário de Obra
* **Registro Diário:** Anotações sobre condições climáticas, atividades realizadas e ocorrências/imprevistos.
* **Histórico:** Navegação fácil por data para consultar dias anteriores.

### 🦺 Controle de EPI
* **Rastreabilidade:** Registro de entrega de equipamentos de proteção individual por funcionário e data.

### 🧮 Calculadoras Integradas
* **Alvenaria:** Cálculo de tijolos baseado na área da parede.
* **Concreto:** Cálculo preciso de volume e quantidade de sacos de cimento, areia e brita, com **Traço Personalizável** (ex: 1:2:3).

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.12
* **Interface Gráfica:** PySide6 (Qt)
* **Banco de Dados:** SQLite3 (Arquivo local `obra_gestor.db` com migração automática de esquema)

---

## ⚙️ Como Rodar o Projeto

### Pré-requisitos
* Python 3.12 instalado.

### Instalação

1.  **Clone ou baixe o repositório:**
    ```bash
    git clone [https://github.com/Miizaa/Gestor-Obra.git](https://github.com/miizaa/gestor-obra.git)
    cd gestor-de-obras
    ```

2.  **Crie um ambiente virtual (Recomendado):**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate  # No Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install pyside6
    ```

4.  **Execute o aplicativo:**
    ```bash
    python obra.py
    ```

---

## 📝 Licença

Este projeto é de uso pessoal e privado.
Desenvolvido por **[Amizael Alves/Miiza]**.

---
*Desenvolvido em 2026.*
