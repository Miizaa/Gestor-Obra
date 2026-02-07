import contextlib
import sys
import os
import ctypes
import sqlite3
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QTabWidget, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QDateEdit, QComboBox, QMessageBox, 
                               QGroupBox, QGridLayout, QFrame, QSplitter, QAbstractItemView,
                               QDialog, QListWidget, QListWidgetItem, QMenu, QDoubleSpinBox,
                               QSizePolicy, QTextEdit)
from PySide6.QtCore import Qt, QDate, QSettings, QLocale 
from PySide6.QtGui import QIcon, QFont, QAction

# --- UTILITÁRIO DE CAMINHO ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 1. BANCO DE DADOS ---
class Database:
    def __init__(self, db_name="obra_gestor.db"): 
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_tables() 

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS obras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL, endereco TEXT, data_inicio TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER, 
                nome TEXT, funcao TEXT, data_admissao TEXT, telefone TEXT,
                cpf TEXT, rg TEXT, banco TEXT, agencia TEXT, conta TEXT,
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY(obra_id) REFERENCES obras(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS presenca (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                func_id INTEGER, 
                data TEXT, 
                manha INTEGER DEFAULT 0,
                tarde INTEGER DEFAULT 0,
                UNIQUE(func_id, data)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER, 
                item TEXT NOT NULL, 
                categoria TEXT, 
                unidade TEXT NOT NULL, 
                quantidade REAL DEFAULT 0,
                FOREIGN KEY(obra_id) REFERENCES obras(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER, 
                data TEXT, 
                tipo TEXT, 
                quantidade REAL, 
                origem TEXT, 
                destino TEXT, 
                nota_fiscal TEXT,
                FOREIGN KEY(item_id) REFERENCES estoque(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS diario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER,
                data TEXT,
                clima TEXT,
                atividades TEXT,
                ocorrencias TEXT,
                UNIQUE(obra_id, data)
            )
        """)
        # ATUALIZADO: Tabela financeiro com nota_fiscal
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS financeiro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER,
                data TEXT,
                tipo TEXT,
                valor REAL,
                descricao TEXT,
                nota_fiscal TEXT,
                FOREIGN KEY(obra_id) REFERENCES obras(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS epi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER,
                func_id INTEGER,
                data TEXT,
                item TEXT,
                FOREIGN KEY(obra_id) REFERENCES obras(id),
                FOREIGN KEY(func_id) REFERENCES funcionarios(id)
            )
        """)
        self.conn.commit()

    def migrate_tables(self):
        # Migrações anteriores
        if not self.check_column_exists("funcionarios", "data_admissao"):
            self.cursor.execute("ALTER TABLE funcionarios ADD COLUMN data_admissao TEXT")
        if not self.check_column_exists("funcionarios", "telefone"):
            self.cursor.execute("ALTER TABLE funcionarios ADD COLUMN telefone TEXT")
        if not self.check_column_exists("funcionarios", "ativo"):
            self.cursor.execute("ALTER TABLE funcionarios ADD COLUMN ativo INTEGER DEFAULT 1")
        if not self.check_column_exists("estoque", "categoria"):
            self.cursor.execute("ALTER TABLE estoque ADD COLUMN categoria TEXT DEFAULT 'Geral'")
        if not self.check_column_exists("movimentacoes", "origem"):
            self.cursor.execute("ALTER TABLE movimentacoes ADD COLUMN origem TEXT")
            if self.check_column_exists("movimentacoes", "fornecedor"):
                self.cursor.execute("UPDATE movimentacoes SET origem = fornecedor")
        if not self.check_column_exists("movimentacoes", "destino"):
            self.cursor.execute("ALTER TABLE movimentacoes ADD COLUMN destino TEXT")
        if not self.check_column_exists("presenca", "manha"):
            self.cursor.execute("ALTER TABLE presenca ADD COLUMN manha INTEGER DEFAULT 0")
            self.cursor.execute("ALTER TABLE presenca ADD COLUMN tarde INTEGER DEFAULT 0")
            if self.check_column_exists("presenca", "presente"):
                self.cursor.execute("UPDATE presenca SET manha=1, tarde=1 WHERE presente=1")
        
        # NOVA MIGRAÇÃO: Nota Fiscal no Financeiro
        if not self.check_column_exists("financeiro", "nota_fiscal"):
            print("Migrando: Adicionando Nota Fiscal ao financeiro...")
            self.cursor.execute("ALTER TABLE financeiro ADD COLUMN nota_fiscal TEXT")
            
        self.conn.commit()

    def check_column_exists(self, table_name, column_name):
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in self.cursor.fetchall()]
        return column_name in columns

    # --- MÉTODOS DE OBRAS ---
    def criar_obra(self, nome, endereco):
        self.cursor.execute("INSERT INTO obras (nome, endereco, data_inicio) VALUES (?, ?, ?)", 
                            (nome, endereco, QDate.currentDate().toString("yyyy-MM-dd")))
        self.conn.commit()
    def get_obras(self):
        self.cursor.execute("SELECT * FROM obras ORDER BY id DESC")
        return self.cursor.fetchall()

    # --- FUNCIONÁRIOS ---
    def add_funcionario(self, obra_id, *args):
        try:
            self.cursor.execute("""
                INSERT INTO funcionarios (obra_id, nome, funcao, data_admissao, telefone, cpf, rg, banco, agencia, conta, ativo) 
                VALUES (?,?,?,?,?,?,?,?,?,?,1)""", (obra_id, *args))
            self.conn.commit(); return True
        except: return False

    def update_funcionario(self, fid, *args):
        try:
            self.cursor.execute("""
                UPDATE funcionarios 
                SET nome=?, funcao=?, data_admissao=?, telefone=?, cpf=?, rg=?, banco=?, agencia=?, conta=? 
                WHERE id=?""", (*args, fid))
            self.conn.commit(); return True
        except: return False

    def toggle_ativo_funcionario(self, fid, status):
        self.cursor.execute("UPDATE funcionarios SET ativo=? WHERE id=?", (status, fid))
        self.conn.commit()

    def get_funcionarios(self, obra_id, apenas_ativos=True):
        cols = "id, obra_id, nome, funcao, data_admissao, telefone, cpf, rg, banco, agencia, conta, ativo"
        if apenas_ativos:
            self.cursor.execute(f"SELECT {cols} FROM funcionarios WHERE obra_id=? AND ativo=1 ORDER BY nome ASC", (obra_id,))
        else:
            self.cursor.execute(f"SELECT {cols} FROM funcionarios WHERE obra_id=? AND ativo=0 ORDER BY nome ASC", (obra_id,))
        return self.cursor.fetchall()
    
    def get_funcionario_by_id(self, fid):
        cols = "id, obra_id, nome, funcao, data_admissao, telefone, cpf, rg, banco, agencia, conta, ativo"
        self.cursor.execute(f"SELECT {cols} FROM funcionarios WHERE id=?", (fid,))
        return self.cursor.fetchone()

    # --- MÉTODOS DE PRESENÇA ---
    def salvar_presenca(self, func_id, data, manha, tarde):
        self.cursor.execute("""
            INSERT INTO presenca (func_id, data, manha, tarde) 
            VALUES (?,?,?,?) 
            ON CONFLICT(func_id, data) 
            DO UPDATE SET manha=excluded.manha, tarde=excluded.tarde
        """, (func_id, data, 1 if manha else 0, 1 if tarde else 0))
        self.conn.commit()
    
    def get_presenca_dia(self, obra_id, data):
        self.cursor.execute("""
            SELECT p.func_id, p.manha, p.tarde FROM presenca p
            JOIN funcionarios f ON p.func_id = f.id
            WHERE f.obra_id = ? AND p.data = ?
        """, (obra_id, data))
        resultado = {}
        for r in self.cursor.fetchall(): resultado[r[0]] = {'m': r[1], 't': r[2]}
        return resultado
    
    def relatorio_periodo(self, obra_id, d1, d2):
        self.cursor.execute("""
            SELECT f.nome, f.funcao, f.data_admissao, f.telefone, 
                   SUM(COALESCE(p.manha, 0) + COALESCE(p.tarde, 0)) * 0.5 as dias, 
                   f.cpf, f.rg, f.banco, f.agencia, f.conta 
            FROM funcionarios f 
            LEFT JOIN presenca p ON f.id=p.func_id AND p.data BETWEEN ? AND ? 
            WHERE f.obra_id = ?
            GROUP BY f.id ORDER BY f.nome ASC""", (d1, d2, obra_id))
        return self.cursor.fetchall()

    # --- MÉTODOS DE ESTOQUE ---
    def add_material(self, obra_id, item, categoria, unidade):
        self.cursor.execute("INSERT INTO estoque (obra_id, item, categoria, unidade, quantidade) VALUES (?, ?, ?, ?, 0)", (obra_id, item, categoria, unidade))
        self.conn.commit()
    def update_material(self, item_id, item, categoria, unidade, quantidade):
        self.cursor.execute("UPDATE estoque SET item=?, categoria=?, unidade=?, quantidade=? WHERE id=?", (item, categoria, unidade, quantidade, item_id))
        self.conn.commit()
    def get_estoque(self, obra_id):
        cols = "id, obra_id, item, categoria, unidade, quantidade"
        self.cursor.execute(f"SELECT {cols} FROM estoque WHERE obra_id=? ORDER BY item ASC", (obra_id,))
        return self.cursor.fetchall()
    def get_material_by_id(self, item_id):
        cols = "id, obra_id, item, categoria, unidade, quantidade"
        self.cursor.execute(f"SELECT {cols} FROM estoque WHERE id=?", (item_id,))
        return self.cursor.fetchone()
    def get_historico(self, obra_id, filtro_item="", filtro_origem="", filtro_tipo="Todos", filtro_cat="Todas"):
        query = """
            SELECT m.id, m.data, e.item, e.categoria, m.tipo, m.quantidade, e.unidade, m.origem, m.destino, m.nota_fiscal 
            FROM movimentacoes m 
            JOIN estoque e ON m.item_id = e.id 
            WHERE e.obra_id = ? 
        """
        params = [obra_id]
        if filtro_item: query += " AND e.item LIKE ?"; params.append(f"%{filtro_item}%")
        if filtro_origem: 
            query += " AND (m.origem LIKE ? OR m.destino LIKE ?)"
            params.append(f"%{filtro_origem}%"); params.append(f"%{filtro_origem}%")
        if filtro_tipo != "Todos":
            tipo_db = "entrada" if filtro_tipo == "Entrada" else "saida"
            query += " AND m.tipo = ?"; params.append(tipo_db)
        if filtro_cat != "Todas": query += " AND e.categoria = ?"; params.append(filtro_cat)
        query += " ORDER BY m.data DESC, m.id DESC"
        self.cursor.execute(query, params); return self.cursor.fetchall()
    
    def movimentar_estoque(self, item_id, qtd, tipo, data, origem, destino, nf):
        fator = 1 if tipo == "entrada" else -1
        self.cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE id = ?", (qtd * fator, item_id))
        self.cursor.execute("""
            INSERT INTO movimentacoes (item_id, data, tipo, quantidade, origem, destino, nota_fiscal) 
            VALUES (?,?,?,?,?,?,?)
        """, (item_id, data, tipo, qtd, origem, destino, nf))
        self.conn.commit()

    def excluir_movimentacao(self, mov_id):
        self.cursor.execute("SELECT item_id, quantidade, tipo FROM movimentacoes WHERE id=?", (mov_id,))
        mov = self.cursor.fetchone()
        if not mov: return False
        item_id, qtd, tipo = mov
        fator_reverso = -1 if tipo == 'entrada' else 1
        try:
            self.cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE id = ?", (qtd * fator_reverso, item_id))
            self.cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (mov_id,))
            self.conn.commit(); return True
        except: self.conn.rollback(); return False

    # --- MÉTODOS DIÁRIO DE OBRA ---
    def save_diario(self, obra_id, data, clima, ativ, ocor):
        self.cursor.execute("""
            INSERT INTO diario (obra_id, data, clima, atividades, ocorrencias) 
            VALUES (?,?,?,?,?) 
            ON CONFLICT(obra_id, data) 
            DO UPDATE SET clima=excluded.clima, atividades=excluded.atividades, ocorrencias=excluded.ocorrencias
        """, (obra_id, data, clima, ativ, ocor))
        self.conn.commit()

    def get_diario(self, obra_id, data):
        self.cursor.execute("SELECT clima, atividades, ocorrencias FROM diario WHERE obra_id=? AND data=?", (obra_id, data))
        return self.cursor.fetchone()

    # --- MÉTODOS FINANCEIRO (Atualizado com NF) ---
    def add_financeiro(self, obra_id, data, tipo, valor, desc, nf):
        self.cursor.execute("INSERT INTO financeiro (obra_id, data, tipo, valor, descricao, nota_fiscal) VALUES (?,?,?,?,?,?)", (obra_id, data, tipo, valor, desc, nf))
        self.conn.commit()
    
    def get_financeiro(self, obra_id):
        self.cursor.execute("SELECT id, data, tipo, valor, descricao, nota_fiscal FROM financeiro WHERE obra_id=? ORDER BY data DESC, id DESC", (obra_id,))
        return self.cursor.fetchall()
    
    def delete_financeiro(self, fin_id):
        try: self.cursor.execute("DELETE FROM financeiro WHERE id=?", (fin_id,)); self.conn.commit(); return True
        except: return False

    # --- MÉTODOS EPI ---
    def add_epi(self, obra_id, func_id, data, item):
        self.cursor.execute("INSERT INTO epi (obra_id, func_id, data, item) VALUES (?,?,?,?)", (obra_id, func_id, data, item))
        self.conn.commit()
        
    def get_epi_historico(self, obra_id):
        self.cursor.execute("""
            SELECT e.id, e.data, f.nome, e.item 
            FROM epi e 
            JOIN funcionarios f ON e.func_id = f.id 
            WHERE e.obra_id = ? ORDER BY e.data DESC
        """, (obra_id,))
        return self.cursor.fetchall()
    
    def delete_epi(self, epi_id):
        try: self.cursor.execute("DELETE FROM epi WHERE id=?", (epi_id,)); self.conn.commit(); return True
        except: return False

# --- 2. SELETOR DE OBRAS ---
class ProjectSelector(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db; self.selected_obra = None
        self.setWindowTitle("Selecione a Obra")
        try: self.setWindowIcon(QIcon(resource_path("icone_obra.ico")))
        except: pass
        self.resize(500, 400); self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        lbl_title = QLabel("🚧 Minhas Obras")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(lbl_title)
        self.list_obras = QListWidget()
        self.list_obras.setStyleSheet("font-size: 14px; padding: 5px;")
        self.list_obras.itemDoubleClicked.connect(self.abrir_obra)
        layout.addWidget(self.list_obras)
        btn_open = QPushButton("Abrir Obra Selecionada")
        btn_open.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        btn_open.clicked.connect(self.abrir_obra)
        layout.addWidget(btn_open)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); layout.addWidget(line)
        gb_new = QGroupBox("Criar Nova Obra"); lay_new = QHBoxLayout()
        self.in_nome = QLineEdit(); self.in_nome.setPlaceholderText("Nome da Obra")
        self.in_end = QLineEdit(); self.in_end.setPlaceholderText("Endereço")
        btn_create = QPushButton("Criar"); btn_create.clicked.connect(self.criar_obra)
        lay_new.addWidget(self.in_nome); lay_new.addWidget(self.in_end); lay_new.addWidget(btn_create)
        gb_new.setLayout(lay_new); layout.addWidget(gb_new); self.setLayout(layout); self.load_list()

    def load_list(self):
        self.list_obras.clear(); obras = self.db.get_obras()
        for o in obras:
            item = QListWidgetItem(f"{o[1]}  (📍 {o[2]})"); item.setData(Qt.UserRole, o); self.list_obras.addItem(item)
    def criar_obra(self):
        if self.in_nome.text():
            self.db.criar_obra(self.in_nome.text(), self.in_end.text())
            self.in_nome.clear(); self.in_end.clear(); self.load_list(); QMessageBox.information(self, "Sucesso", "Nova obra criada!")
    def abrir_obra(self):
        current_item = self.list_obras.currentItem()
        if current_item: self.selected_obra = current_item.data(Qt.UserRole); self.accept()
        else: QMessageBox.warning(self, "Aviso", "Selecione uma obra.")

# --- 3. GERENCIAR INATIVOS ---
class InactiveEmployeesDialog(QDialog):
    def __init__(self, db, obra_id):
        super().__init__()
        self.db = db; self.obra_id = obra_id
        self.setWindowTitle("Funcionários Inativos / Dispensados")
        self.resize(600, 400); layout = QVBoxLayout()
        layout.addWidget(QLabel("Lista de Funcionários Inativos (Selecione para reativar)"))
        self.tb = QTableWidget(0, 3); self.tb.setHorizontalHeaderLabels(["ID", "Nome", "Função"])
        self.tb.setColumnHidden(0, True); self.tb.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.tb)
        btn_reactivate = QPushButton("♻️ Reativar Funcionário Selecionado")
        btn_reactivate.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        btn_reactivate.clicked.connect(self.reactivate); layout.addWidget(btn_reactivate); self.setLayout(layout); self.load_data()

    def load_data(self):
        data = self.db.get_funcionarios(self.obra_id, apenas_ativos=False)
        self.tb.setRowCount(0)
        for r, d in enumerate(data):
            self.tb.insertRow(r); self.tb.setItem(r, 0, QTableWidgetItem(str(d[0])))
            self.tb.setItem(r, 1, QTableWidgetItem(d[2])); self.tb.setItem(r, 2, QTableWidgetItem(d[3]))

    def reactivate(self):
        rows = self.tb.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self, "Aviso", "Selecione um funcionário."); return
        fid = int(self.tb.item(rows[0].row(), 0).text()); nome = self.tb.item(rows[0].row(), 1).text()
        if QMessageBox.question(self, "Confirmar", f"Reativar {nome}?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.db.toggle_ativo_funcionario(fid, 1); QMessageBox.information(self, "Sucesso", "Reativado!"); self.load_data()

# --- 4. DIALOGO DE EDIÇÃO DE MATERIAL ---
class EditMaterialDialog(QDialog):
    def __init__(self, db, item_id):
        super().__init__()
        self.db = db; self.item_id = item_id
        self.setWindowTitle("Editar Item / Correção")
        self.setModal(True); self.setup_ui(); self.load_data()

    def setup_ui(self):
        l = QVBoxLayout(); g = QGridLayout()
        self.in_item = QLineEdit()
        self.cb_cat = QComboBox(); self.cb_cat.addItems(["Geral", "Hidráulica", "Elétrica", "Pintura", "Alvenaria", "Acabamento", "Ferramentas"])
        self.cb_unit = QComboBox(); self.cb_unit.addItems(["Unidade", "Saco", "m³", "Metro", "Kg", "Barra", "Lata", "Caixa", "Par"])
        self.sp_qtd = QDoubleSpinBox(); self.sp_qtd.setRange(-10000, 10000); self.sp_qtd.setDecimals(2)
        g.addWidget(QLabel("Nome:"), 0, 0); g.addWidget(self.in_item, 0, 1)
        g.addWidget(QLabel("Categoria:"), 1, 0); g.addWidget(self.cb_cat, 1, 1)
        g.addWidget(QLabel("Unidade:"), 2, 0); g.addWidget(self.cb_unit, 2, 1)
        g.addWidget(QLabel("Saldo Atual:"), 3, 0); g.addWidget(self.sp_qtd, 3, 1)
        btn_save = QPushButton("Salvar Alterações"); btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;"); btn_save.clicked.connect(self.save)
        l.addLayout(g); l.addWidget(btn_save); self.setLayout(l)

    def load_data(self):
        data = self.db.get_material_by_id(self.item_id)
        if data:
            self.in_item.setText(data[2]); self.cb_cat.setCurrentText(data[3] if data[3] else "Geral")
            self.cb_unit.setCurrentText(data[4]); self.sp_qtd.setValue(data[5])

    def save(self):
        self.db.update_material(self.item_id, self.in_item.text(), self.cb_cat.currentText(), self.cb_unit.currentText(), self.sp_qtd.value())
        QMessageBox.information(self, "Sucesso", "Item atualizado!"); self.accept()

# --- 5. ABAS DE GESTÃO ---

class EmployeeManager(QWidget):
    def __init__(self, db, obra_id):
        super().__init__(); self.db = db; self.obra_id = obra_id; self.eid = None
        layout = QVBoxLayout()
        gb = QGroupBox("Cadastro de Funcionário"); g = QGridLayout()
        self.n = QLineEdit(); self.f = QComboBox()
        self.f.addItems(sorted(["Pedreiro", "Servente", "Mestre", "Encarregado", "Eletricista", "Pintor", "Encanador", "Estagiário", "Engenheiro", "Soldador"]))
        self.d_adm = QDateEdit(); self.d_adm.setCalendarPopup(True); self.d_adm.setDate(QDate.currentDate()); self.d_adm.setDisplayFormat("dd/MM/yyyy") 
        self.tel = QLineEdit(); self.cpf = QLineEdit(); self.rg = QLineEdit(); self.b = QLineEdit(); self.ag = QLineEdit(); self.c = QLineEdit()
        [w.setPlaceholderText(t) for w, t in zip([self.n, self.tel, self.cpf, self.rg, self.b, self.ag, self.c], ["Nome", "Telefone", "CPF", "RG", "Banco", "Agência", "Conta"])]
        bt_save = QPushButton("Salvar"); bt_save.clicked.connect(self.sv)
        bt_clear = QPushButton("Limpar"); bt_clear.clicked.connect(self.rst)
        self.bt_del = QPushButton("❌ Desativar"); self.bt_del.setStyleSheet("background-color: #F44336; color: white;")
        self.bt_del.clicked.connect(self.desativar); self.bt_del.setVisible(False)
        g.addWidget(QLabel("Nome:"),0,0); g.addWidget(self.n,0,1); g.addWidget(self.f,0,2)
        g.addWidget(QLabel("Doc:"),1,0); g.addWidget(self.cpf,1,1); g.addWidget(self.rg,1,2)
        g.addWidget(QLabel("Admissão:"),1,3); g.addWidget(self.d_adm,1,4); g.addWidget(QLabel("Telefone:"),0,3); g.addWidget(self.tel,0,4) 
        g.addWidget(QLabel("Banc:"),2,0); g.addWidget(self.b,2,1); g.addWidget(self.ag,2,2); g.addWidget(self.c,2,3)
        hbox_btns = QHBoxLayout(); hbox_btns.addWidget(bt_clear); hbox_btns.addWidget(self.bt_del); hbox_btns.addWidget(bt_save)
        g.addLayout(hbox_btns, 3, 0, 1, 5); gb.setLayout(g)
        self.dt = QDateEdit(); self.dt.setCalendarPopup(True); self.dt.setDate(QDate.currentDate()); self.dt.dateChanged.connect(self.ld); self.dt.setDisplayFormat("dd/MM/yyyy")
        
        colunas = ["ID", "Nome", "Função", "Admissão", "Telefone", "CPF", "RG", "Banco", "Agência", "Conta", "M", "T"]
        self.tb = QTableWidget(0, len(colunas)); self.tb.setHorizontalHeaderLabels(colunas); self.tb.setColumnHidden(0, True)
        self.tb.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive); self.tb.cellDoubleClicked.connect(self.ed)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tb.setColumnWidth(10, 30); self.tb.setColumnWidth(11, 30)
        
        bp = QPushButton("💾 Salvar Presença"); bp.setStyleSheet("background-color:#4CAF50;color:white;font-weight:bold"); bp.clicked.connect(self.svp)
        layout.addWidget(gb); layout.addWidget(self.dt); layout.addWidget(self.tb); layout.addWidget(bp); self.setLayout(layout); self.ld()

    def save_table_state(self):
        QSettings("MiizaSoft", "GestorObras").setValue("emp_table_state", self.tb.horizontalHeader().saveState())
    def load_table_state(self):
        if val := QSettings("MiizaSoft", "GestorObras").value("emp_table_state"): self.tb.horizontalHeader().restoreState(val)

    def sv(self):
        s_adm = self.d_adm.date().toString("yyyy-MM-dd")
        a = (self.n.text(), self.f.currentText(), s_adm, self.tel.text(), self.cpf.text(), self.rg.text(), self.b.text(), self.ag.text(), self.c.text())
        if not a[0]: return
        if self.eid: self.db.update_funcionario(self.eid, *a)
        else: self.db.add_funcionario(self.obra_id, *a)
        self.rst(); self.ld()

    def ed(self, r, c):
        id = int(self.tb.item(r, 0).text()); d = self.db.get_funcionario_by_id(id); self.eid = id
        self.n.setText(d[2]); self.f.setCurrentText(d[3])
        try: self.d_adm.setDate(QDate.fromString(d[4], "yyyy-MM-dd"))
        except: self.d_adm.setDate(QDate.currentDate())
        self.tel.setText(d[5]); self.cpf.setText(d[6]); self.rg.setText(d[7]); self.b.setText(d[8]); self.ag.setText(d[9]); self.c.setText(d[10]); self.bt_del.setVisible(True)

    def desativar(self):
        if not self.eid: return
        if QMessageBox.question(self, "Atenção", "Deseja desativar este funcionário?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.db.toggle_ativo_funcionario(self.eid, 0); self.rst(); self.ld(); QMessageBox.information(self, "Ok", "Funcionário movido para Inativos.")

    def rst(self): 
        self.eid=None; self.n.clear(); self.cpf.clear(); self.rg.clear(); self.tel.clear(); self.b.clear(); self.ag.clear(); self.c.clear(); self.d_adm.setDate(QDate.currentDate()); self.bt_del.setVisible(False)

    def ld(self):
        fs = self.db.get_funcionarios(self.obra_id); p = self.db.get_presenca_dia(self.obra_id, self.dt.date().toString("yyyy-MM-dd"))
        self.tb.setRowCount(0)
        for r, d in enumerate(fs):
            self.tb.insertRow(r)
            try: fmt_adm = QDate.fromString(d[4], "yyyy-MM-dd").toString("dd/MM/yyyy")
            except: fmt_adm = d[4]
            self.tb.setItem(r,0,QTableWidgetItem(str(d[0]))); self.tb.setItem(r,1,QTableWidgetItem(d[2]))
            self.tb.setItem(r,2,QTableWidgetItem(d[3])); self.tb.setItem(r,3,QTableWidgetItem(fmt_adm))
            self.tb.setItem(r,4,QTableWidgetItem(d[5])); self.tb.setItem(r,5,QTableWidgetItem(d[6])); self.tb.setItem(r,6,QTableWidgetItem(d[7]))
            self.tb.setItem(r,7,QTableWidgetItem(d[8])); self.tb.setItem(r,8,QTableWidgetItem(d[9])); self.tb.setItem(r,9,QTableWidgetItem(d[10]))
            
            status = p.get(d[0], {'m': 0, 't': 0})
            ch_m = QTableWidgetItem(); ch_m.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            ch_m.setCheckState(Qt.Checked if status['m'] else Qt.Unchecked)
            self.tb.setItem(r, 10, ch_m)
            ch_t = QTableWidgetItem(); ch_t.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            ch_t.setCheckState(Qt.Checked if status['t'] else Qt.Unchecked)
            self.tb.setItem(r, 11, ch_t)
            
    def svp(self):
        d = self.dt.date().toString("yyyy-MM-dd")
        for r in range(self.tb.rowCount()): 
            fid = int(self.tb.item(r,0).text())
            manha = self.tb.item(r, 10).checkState() == Qt.Checked
            tarde = self.tb.item(r, 11).checkState() == Qt.Checked
            self.db.salvar_presenca(fid, d, manha, tarde)
        QMessageBox.information(self,"Ok","Salvo")

class StockControl(QWidget):
    def __init__(self, db, obra_id):
        super().__init__(); self.db = db; self.obra_id = obra_id; self.sid = None
        main = QHBoxLayout()
        lw = QWidget(); ll = QVBoxLayout()
        ll.addWidget(QLabel("📦 Saldo da Obra"))
        self.tb_s = QTableWidget(0,4); self.tb_s.setHorizontalHeaderLabels(["ID", "Item", "Categoria", "Qtd"])
        self.tb_s.setColumnHidden(0,True); self.tb_s.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.tb_s.setSelectionBehavior(QAbstractItemView.SelectRows); self.tb_s.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tb_s.cellClicked.connect(self.sel)
        btn_edit_item = QPushButton("✏️ Editar Item"); btn_edit_item.clicked.connect(self.edit_item)
        ll.addWidget(self.tb_s); ll.addWidget(btn_edit_item)
        
        ll.addWidget(QLabel("📜 Histórico"))
        filter_layout = QHBoxLayout()
        self.f_item = QLineEdit(); self.f_item.setPlaceholderText("Filtrar Material...")
        self.f_origem = QLineEdit(); self.f_origem.setPlaceholderText("Filtrar Origem/Destino...")
        self.f_cat = QComboBox(); self.f_cat.addItems(["Todas", "Geral", "Hidráulica", "Elétrica", "Pintura", "Alvenaria", "Acabamento", "Ferramentas"])
        self.f_tipo = QComboBox(); self.f_tipo.addItems(["Todos", "Entrada", "Saída"])
        btn_filter = QPushButton("🔍 Filtrar"); btn_filter.clicked.connect(self.load_history)
        btn_del = QPushButton("🗑️ Excluir Mov."); btn_del.setStyleSheet("background-color: #F44336; color: white;")
        btn_del.clicked.connect(self.delete_move)
        
        self.f_item.textChanged.connect(self.load_history); self.f_origem.textChanged.connect(self.load_history)
        self.f_tipo.currentTextChanged.connect(self.load_history); self.f_cat.currentTextChanged.connect(self.load_history)
        filter_layout.addWidget(self.f_item); filter_layout.addWidget(self.f_cat)
        filter_layout.addWidget(self.f_origem); filter_layout.addWidget(self.f_tipo)
        filter_layout.addWidget(btn_filter)
        ll.addLayout(filter_layout); ll.addWidget(btn_del)
        
        self.tb_h = QTableWidget(0,9) 
        self.tb_h.setHorizontalHeaderLabels(["ID","Data","Item","Categoria","Tipo","Qtd","Origem","Destino", "NF"])
        self.tb_h.setColumnHidden(0,True); self.tb_h.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive); self.tb_h.horizontalHeader().setStretchLastSection(True) 
        self.tb_h.setSelectionBehavior(QAbstractItemView.SelectRows)
        ll.addWidget(self.tb_h); lw.setLayout(ll)
        
        rw = QWidget(); rw.setMaximumWidth(300); rl = QVBoxLayout()
        gb1 = QGroupBox("Novo Item"); gl1 = QGridLayout()
        self.in_i = QLineEdit(); self.in_i.setPlaceholderText("Nome do Item")
        self.cb_cat = QComboBox(); self.cb_cat.addItems(["Geral", "Hidráulica", "Elétrica", "Pintura", "Alvenaria", "Acabamento", "Ferramentas"])
        self.cb_u = QComboBox(); self.cb_u.addItems(["Unidade", "Saco", "m³", "Metro", "Kg", "Barra", "Lata", "Caixa"])
        b1 = QPushButton("Cadastrar"); b1.clicked.connect(self.add)
        gl1.addWidget(QLabel("Nome:"),0,0); gl1.addWidget(self.in_i,0,1)
        gl1.addWidget(QLabel("Categoria:"),1,0); gl1.addWidget(self.cb_cat,1,1)
        gl1.addWidget(QLabel("Unid:"),2,0); gl1.addWidget(self.cb_u,2,1)
        gl1.addWidget(b1,3,0,1,2); gb1.setLayout(gl1)
        
        gb2 = QGroupBox("Movimentação"); gl2 = QVBoxLayout()
        self.lb_s = QLabel("Selecione..."); self.lb_s.setStyleSheet("color:red")
        self.dt = QDateEdit(); self.dt.setCalendarPopup(True); self.dt.setDate(QDate.currentDate()); self.dt.setDisplayFormat("dd/MM/yyyy")
        self.in_q = QLineEdit(); self.in_q.setPlaceholderText("Qtd")
        self.in_origem = QLineEdit(); self.in_origem.setPlaceholderText("Origem")
        self.in_dest = QLineEdit(); self.in_dest.setPlaceholderText("Destino")
        self.in_nf = QLineEdit(); self.in_nf.setPlaceholderText("Nota Fiscal")
        h = QHBoxLayout(); bin = QPushButton("Entrada"); bin.clicked.connect(lambda: self.mov("entrada")); bout=QPushButton("Saída"); bout.clicked.connect(lambda: self.mov("saida"))
        h.addWidget(bin); h.addWidget(bout)
        gl2.addWidget(self.lb_s); gl2.addWidget(self.dt); gl2.addWidget(self.in_q); gl2.addWidget(self.in_origem); gl2.addWidget(self.in_dest); gl2.addWidget(self.in_nf); gl2.addLayout(h); gb2.setLayout(gl2)
        rl.addWidget(gb1); rl.addWidget(gb2); rl.addStretch(); rw.setLayout(rl)
        main.addWidget(lw); main.addWidget(rw); self.setLayout(main); self.ref()
    
    def save_table_state(self):
        QSettings("MiizaSoft", "GestorObras").setValue("stock_bal_state", self.tb_s.horizontalHeader().saveState())
        QSettings("MiizaSoft", "GestorObras").setValue("stock_hist_state", self.tb_h.horizontalHeader().saveState())
    def load_table_state(self):
        if v := QSettings("MiizaSoft", "GestorObras").value("stock_bal_state"): self.tb_s.horizontalHeader().restoreState(v)
        if v := QSettings("MiizaSoft", "GestorObras").value("stock_hist_state"): self.tb_h.horizontalHeader().restoreState(v)

    def add(self):
        if self.in_i.text(): self.db.add_material(self.obra_id, self.in_i.text(), self.cb_cat.currentText(), self.cb_u.currentText()); self.in_i.clear(); self.ref()
    def sel(self, r, c): 
        try: self.sid=int(self.tb_s.item(r,0).text()); self.lb_s.setText(self.tb_s.item(r,1).text()); self.lb_s.setStyleSheet("color:green")
        except: pass
    def mov(self, t):
        if not self.sid: return
        with contextlib.suppress(Exception):
            data_iso = self.dt.date().toString("yyyy-MM-dd")
            self.db.movimentar_estoque(self.sid, float(self.in_q.text().replace(',','.')), t, data_iso, self.in_origem.text(), self.in_dest.text(), self.in_nf.text())
            self.ref()
    def delete_move(self):
        rows = self.tb_h.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self, "Aviso", "Selecione uma movimentação."); return
        mov_id = int(self.tb_h.item(rows[0].row(), 0).text())
        if QMessageBox.question(self, "Confirmar", "Excluir movimentação?", QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            if self.db.excluir_movimentacao(mov_id): self.ref()
    def edit_item(self):
        rows = self.tb_s.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self, "Aviso", "Selecione um item na tabela de saldo."); return
        item_id = int(self.tb_s.item(rows[0].row(), 0).text())
        dialog = EditMaterialDialog(self.db, item_id); dialog.exec(); self.ref()
    def ref(self):
        self.sid = None; self.lb_s.setText("Selecione..."); self.lb_s.setStyleSheet("color:red")
        est = self.db.get_estoque(self.obra_id); self.tb_s.setRowCount(0)
        for r,d in enumerate(est):
            self.tb_s.insertRow(r); self.tb_s.setItem(r,0,QTableWidgetItem(str(d[0])))
            self.tb_s.setItem(r,1,QTableWidgetItem(d[2]))
            self.tb_s.setItem(r,2,QTableWidgetItem(d[3] or "-")); self.tb_s.setItem(r,3,QTableWidgetItem(f"{d[5]} {d[4]}"))
        self.load_history()
    def load_history(self):
        f_mat = self.f_item.text(); f_orig = self.f_origem.text(); f_tip = self.f_tipo.currentText(); f_cat = self.f_cat.currentText()
        his = self.db.get_historico(self.obra_id, f_mat, f_orig, f_tip, f_cat); self.tb_h.setRowCount(0)
        for r,d in enumerate(his):
            self.tb_h.insertRow(r)
            self.tb_h.setItem(r,0,QTableWidgetItem(str(d[0])))
            try: fmt_dt = QDate.fromString(d[1], "yyyy-MM-dd").toString("dd/MM/yyyy")
            except: fmt_dt = d[1]
            self.tb_h.setItem(r,1,QTableWidgetItem(fmt_dt))
            self.tb_h.setItem(r,2,QTableWidgetItem(d[2])); self.tb_h.setItem(r,3,QTableWidgetItem(d[3] or "-"))
            tipo_item = QTableWidgetItem(d[4].capitalize()); tipo_item.setForeground(Qt.darkGreen if d[4] == "entrada" else Qt.red); self.tb_h.setItem(r,4, tipo_item)
            self.tb_h.setItem(r,5,QTableWidgetItem(f"{d[5]} {d[6]}"))
            self.tb_h.setItem(r,6,QTableWidgetItem(d[7] or "")); self.tb_h.setItem(r,7,QTableWidgetItem(d[8] or "")); self.tb_h.setItem(r,8,QTableWidgetItem(d[9] or ""))

class ReportTab(QWidget):
    def __init__(self, db, obra_id):
        super().__init__(); self.db=db; self.obra_id=obra_id; l=QVBoxLayout()
        d1=QDateEdit(); d2=QDateEdit(); d1.setDate(QDate.currentDate().addDays(-15)); d2.setDate(QDate.currentDate())
        d1.setDisplayFormat("dd/MM/yyyy"); d2.setDisplayFormat("dd/MM/yyyy")
        [d.setCalendarPopup(True) for d in [d1,d2]]
        b = QPushButton("Gerar Relatório"); b.clicked.connect(lambda: self.g(d1.date().toString("yyyy-MM-dd"),d2.date().toString("yyyy-MM-dd")))
        b_copy = QPushButton("📋 Copiar Lista"); b_copy.setStyleSheet("background-color: #008CBA; color: white;"); b_copy.clicked.connect(self.copiar_area_transferencia)
        h=QHBoxLayout(); h.addWidget(d1); h.addWidget(d2); h.addWidget(b); h.addWidget(b_copy); self.t=QTableWidget(0,10)
        self.t.setHorizontalHeaderLabels(["Nome","Função","Admissão","Telefone","Dias","CPF","RG","Banco","Agência","Conta"])
        header = self.t.horizontalHeader(); header.setSectionResizeMode(QHeaderView.Interactive); header.setStretchLastSection(True); self.t.setColumnWidth(0, 200)
        l.addLayout(h); l.addWidget(self.t); self.setLayout(l)
    
    def save_table_state(self):
        QSettings("MiizaSoft", "GestorObras").setValue("report_table_state", self.t.horizontalHeader().saveState())
    def load_table_state(self):
        if val := QSettings("MiizaSoft", "GestorObras").value("report_table_state"): self.t.horizontalHeader().restoreState(val)

    def g(self,d1,d2):
        ds=self.db.relatorio_periodo(self.obra_id, d1, d2); self.t.setRowCount(0)
        for r,row in enumerate(ds): 
            self.t.insertRow(r); self.t.setItem(r, 0, QTableWidgetItem(row[0])); self.t.setItem(r, 1, QTableWidgetItem(row[1]))
            try: fmt = QDate.fromString(row[2], "yyyy-MM-dd").toString("dd/MM/yyyy")
            except: fmt = row[2]
            self.t.setItem(r, 2, QTableWidgetItem(fmt)); self.t.setItem(r, 3, QTableWidgetItem(row[3])) 
            self.t.setItem(r, 4, QTableWidgetItem(str(row[4]))); self.t.setItem(r, 5, QTableWidgetItem(row[5])); self.t.setItem(r, 6, QTableWidgetItem(row[6]))
            self.t.setItem(r, 7, QTableWidgetItem(row[7])); self.t.setItem(r, 8, QTableWidgetItem(row[8])); self.t.setItem(r, 9, QTableWidgetItem(row[9]))
    def copiar_area_transferencia(self):
        lista_final = []; rows = self.t.rowCount()
        for r in range(rows):
            try:
                dias_txt = self.t.item(r, 4).text()
                if float(dias_txt) > 0: lista_final.append(f"{self.t.item(r, 0).text()} - {dias_txt} dias")
            except: continue
        if lista_final: QApplication.clipboard().setText("\n".join(lista_final)); QMessageBox.information(self, "Sucesso", "Copiado!")
        else: QMessageBox.information(self, "Vazio", "Nenhum dado.")

# --- 8. ABA: CALCULADORA DE MATERIAL (AGORA CORRETA) ---
class MaterialCalculator(QWidget): 
    def __init__(self):
        super().__init__()
        l = QVBoxLayout()
        gb1 = QGroupBox("Alvenaria"); g = QGridLayout()
        self.w = QLineEdit(); self.h = QLineEdit(); self.u_w = QComboBox(); self.u_w.addItems(["m", "cm"])
        self.bh = QLineEdit(); self.bl = QLineEdit(); self.u_b = QComboBox(); self.u_b.addItems(["cm", "m"])
        g.addWidget(QLabel("Parede (LxA):"),0,0); g.addWidget(self.w,0,1); g.addWidget(self.h,0,2); g.addWidget(self.u_w, 0, 3)
        g.addWidget(QLabel("Tijolo (LxA):"),1,0); g.addWidget(self.bh,1,1); g.addWidget(self.bl,1,2); g.addWidget(self.u_b, 1, 3)
        b=QPushButton("Calcular"); b.clicked.connect(self.ca); self.ra=QLabel("Aguardando cálculo...")
        self.ra.setStyleSheet("font-weight: bold; color: #f2ff00; font-size: 14px; background-color: #333; padding: 5px; border-radius: 4px;") 
        g.addWidget(b,2,0,1,4); g.addWidget(self.ra,3,0,1,4)
        gb1.setLayout(g)
        
        gb2 = QGroupBox("Cálculo de Concreto (Traço)"); g2 = QGridLayout()
        self.sp_c = QDoubleSpinBox(); self.sp_c.setValue(1.0); self.sp_c.setPrefix("Cim: ")
        self.sp_a = QDoubleSpinBox(); self.sp_a.setValue(2.0); self.sp_a.setPrefix("Are: ")
        self.sp_b = QDoubleSpinBox(); self.sp_b.setValue(3.0); self.sp_b.setPrefix("Bri: ")
        h_traco = QHBoxLayout(); h_traco.addWidget(self.sp_c); h_traco.addWidget(self.sp_a); h_traco.addWidget(self.sp_b)
        g2.addWidget(QLabel("Traço (C:A:B):"), 0, 0); g2.addLayout(h_traco, 0, 1, 1, 2)
        self.conc_comp = QLineEdit(); self.uc_comp = QComboBox(); self.uc_comp.addItems(["m", "cm"])
        self.conc_larg = QLineEdit(); self.uc_larg = QComboBox(); self.uc_larg.addItems(["m", "cm"])
        self.conc_esp = QLineEdit(); self.uc_esp = QComboBox(); self.uc_esp.addItems(["m", "cm"])
        g2.addWidget(QLabel("Comprimento:"), 1, 0); g2.addWidget(self.conc_comp, 1, 1); g2.addWidget(self.uc_comp, 1, 2)
        g2.addWidget(QLabel("Largura:"), 2, 0); g2.addWidget(self.conc_larg, 2, 1); g2.addWidget(self.uc_larg, 2, 2)
        g2.addWidget(QLabel("Espessura:"), 3, 0); g2.addWidget(self.conc_esp, 3, 1); g2.addWidget(self.uc_esp, 3, 2)
        btn_calc_conc = QPushButton("Calcular Concreto"); btn_calc_conc.clicked.connect(self.cc)
        self.res_conc = QLabel("Aguardando cálculo...")
        self.res_conc.setStyleSheet("font-weight: bold; color: #f2ff00; font-size: 14px; background-color: #333; padding: 5px; border-radius: 4px;") 
        lay_conc_inner = QVBoxLayout(); lay_conc_inner.addLayout(g2); lay_conc_inner.addWidget(btn_calc_conc); lay_conc_inner.addWidget(self.res_conc)
        gb2.setLayout(lay_conc_inner)
        l.addWidget(gb1); l.addWidget(gb2); l.addStretch(); self.setLayout(l)

    def get_val_in_meters(self, val_text, unit):
        try:
            val = float(val_text.replace(',', '.'))
            if unit == "cm": return val / 100
            return val
        except: return 0.0

    def ca(self):
        try: 
            w = self.get_val_in_meters(self.w.text(), self.u_w.currentText())
            h = self.get_val_in_meters(self.h.text(), self.u_w.currentText())
            bw = self.get_val_in_meters(self.bh.text(), self.u_b.currentText())
            bl = self.get_val_in_meters(self.bl.text(), self.u_b.currentText())
            if bw*bl == 0: raise ValueError
            total = (w * h) / (bw * bl)
            self.ra.setText(f"Total (+10%): {int(total * 1.1)}")
        except: self.ra.setText("Erro")

    def cc(self):
        try:
            comp = self.get_val_in_meters(self.conc_comp.text(), self.uc_comp.currentText())
            larg = self.get_val_in_meters(self.conc_larg.text(), self.uc_larg.currentText())
            esp = self.get_val_in_meters(self.conc_esp.text(), self.uc_esp.currentText())
            vol_m3 = comp * larg * esp
            vol_seco = vol_m3 * 1.52
            part_c = self.sp_c.value(); part_a = self.sp_a.value(); part_b = self.sp_b.value()
            total_parts = part_c + part_a + part_b
            if total_parts == 0: raise ValueError
            vol_cimento = (part_c / total_parts) * vol_seco
            vol_areia = (part_a / total_parts) * vol_seco
            vol_brita = (part_b / total_parts) * vol_seco
            sacos_cimento = (vol_cimento * 1440) / 50
            self.res_conc.setText(f"Vol: {vol_m3:.2f}m³ | Cim: {sacos_cimento:.1f} sc | Areia: {vol_areia:.2f}m³ | Brita: {vol_brita:.2f}m³")
        except: self.res_conc.setText("Erro: Verifique números.")

# --- 9. ABA: DIÁRIO DE OBRA ---
class DiaryTab(QWidget):
    def __init__(self, db, obra_id):
        super().__init__()
        self.db = db; self.obra_id = obra_id
        l = QVBoxLayout()
        h_date = QHBoxLayout()
        h_date.addWidget(QLabel("Data do Diário:"))
        self.dt = QDateEdit(); self.dt.setCalendarPopup(True); self.dt.setDate(QDate.currentDate()); self.dt.setDisplayFormat("dd/MM/yyyy")
        self.dt.dateChanged.connect(self.load_data)
        h_date.addWidget(self.dt); h_date.addStretch()
        l.addLayout(h_date)
        self.txt_clima = QTextEdit(); self.txt_clima.setPlaceholderText("Descreva o clima (Sol, Chuva, etc)..."); self.txt_clima.setMaximumHeight(60)
        self.txt_ativ = QTextEdit(); self.txt_ativ.setPlaceholderText("Atividades realizadas hoje...")
        self.txt_ocor = QTextEdit(); self.txt_ocor.setPlaceholderText("Ocorrências, problemas, faltas de material...")
        l.addWidget(QLabel("🌤️ Condições Climáticas:")); l.addWidget(self.txt_clima)
        l.addWidget(QLabel("🔨 Atividades do Dia:")); l.addWidget(self.txt_ativ)
        l.addWidget(QLabel("⚠️ Ocorrências:")); l.addWidget(self.txt_ocor)
        btn_save = QPushButton("💾 Salvar Diário"); btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_save.clicked.connect(self.save)
        l.addWidget(btn_save)
        self.setLayout(l); self.load_data()
    def load_data(self):
        data = self.db.get_diario(self.obra_id, self.dt.date().toString("yyyy-MM-dd"))
        if data:
            self.txt_clima.setPlainText(data[0]); self.txt_ativ.setPlainText(data[1]); self.txt_ocor.setPlainText(data[2])
        else:
            self.txt_clima.clear(); self.txt_ativ.clear(); self.txt_ocor.clear()
    def save(self):
        self.db.save_diario(self.obra_id, self.dt.date().toString("yyyy-MM-dd"), self.txt_clima.toPlainText(), self.txt_ativ.toPlainText(), self.txt_ocor.toPlainText())
        QMessageBox.information(self, "Sucesso", "Diário salvo!")

# --- 10. ABA: FINANCEIRO (ATUALIZADA COM NF) ---
class FinancialTab(QWidget):
    def __init__(self, db, obra_id):
        super().__init__(); self.db = db; self.obra_id = obra_id
        main = QHBoxLayout()
        lw = QWidget(); ll = QVBoxLayout()
        self.lbl_saldo = QLabel("Saldo: R$ 0.00"); self.lbl_saldo.setStyleSheet("font-size: 18px; font-weight: bold;")
        ll.addWidget(self.lbl_saldo)
        
        # TABELA COM COLUNA NF (6 colunas)
        self.tb = QTableWidget(0, 6); self.tb.setHorizontalHeaderLabels(["ID", "Data", "Tipo", "Valor", "Descrição", "NF"])
        self.tb.setColumnHidden(0, True); self.tb.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        ll.addWidget(self.tb)
        
        btn_del = QPushButton("🗑️ Excluir Lançamento"); btn_del.clicked.connect(self.delete_entry)
        ll.addWidget(btn_del); lw.setLayout(ll)
        
        rw = QWidget(); rw.setMaximumWidth(300); rl = QVBoxLayout()
        gb = QGroupBox("Novo Lançamento"); gl = QGridLayout()
        self.dt = QDateEdit(); self.dt.setCalendarPopup(True); self.dt.setDate(QDate.currentDate()); self.dt.setDisplayFormat("dd/MM/yyyy")
        self.cb_tipo = QComboBox(); self.cb_tipo.addItems(["Saída (Gasto)", "Entrada (Recebimento)"])
        self.sp_valor = QDoubleSpinBox(); self.sp_valor.setRange(0, 1000000); self.sp_valor.setPrefix("R$ ")
        
        # NOVOS CAMPOS
        self.txt_nf = QLineEdit(); self.txt_nf.setPlaceholderText("Nota Fiscal")
        self.txt_desc = QLineEdit(); self.txt_desc.setPlaceholderText("Descrição (Ex: Cimento, Areia, Brita)")
        
        btn_add = QPushButton("Adicionar"); btn_add.clicked.connect(self.add)
        gl.addWidget(QLabel("Data:"),0,0); gl.addWidget(self.dt,0,1)
        gl.addWidget(QLabel("Tipo:"),1,0); gl.addWidget(self.cb_tipo,1,1)
        gl.addWidget(QLabel("Valor:"),2,0); gl.addWidget(self.sp_valor,2,1)
        gl.addWidget(QLabel("NF:"),3,0); gl.addWidget(self.txt_nf,3,1) # Campo NF na grid
        gl.addWidget(QLabel("Desc:"),4,0); gl.addWidget(self.txt_desc,4,1)
        gl.addWidget(btn_add,5,0,1,2); gb.setLayout(gl)
        rl.addWidget(gb); rl.addStretch(); rw.setLayout(rl)
        main.addWidget(lw); main.addWidget(rw); self.setLayout(main); self.load_data()

    def add(self):
        tipo = "saida" if "Saída" in self.cb_tipo.currentText() else "entrada"
        # Passando NF para o banco
        self.db.add_financeiro(self.obra_id, self.dt.date().toString("yyyy-MM-dd"), tipo, self.sp_valor.value(), self.txt_desc.text(), self.txt_nf.text())
        self.txt_desc.clear(); self.txt_nf.clear(); self.sp_valor.setValue(0); self.load_data()

    def load_data(self):
        rows = self.db.get_financeiro(self.obra_id)
        self.tb.setRowCount(0); saldo = 0
        for r, row in enumerate(rows):
            self.tb.insertRow(r)
            self.tb.setItem(r, 0, QTableWidgetItem(str(row[0])))
            try: fmt = QDate.fromString(row[1], "yyyy-MM-dd").toString("dd/MM/yyyy")
            except: fmt = row[1]
            self.tb.setItem(r, 1, QTableWidgetItem(fmt))
            tipo_item = QTableWidgetItem(row[2].upper())
            if row[2] == 'entrada': tipo_item.setForeground(Qt.darkGreen); saldo += row[3]
            else: tipo_item.setForeground(Qt.red); saldo -= row[3]
            self.tb.setItem(r, 2, tipo_item)
            self.tb.setItem(r, 3, QTableWidgetItem(f"R$ {row[3]:.2f}"))
            self.tb.setItem(r, 4, QTableWidgetItem(row[4]))
            self.tb.setItem(r, 5, QTableWidgetItem(row[5] or "")) # NF na tabela
        self.lbl_saldo.setText(f"Saldo: R$ {saldo:.2f}")
        color = "green" if saldo >= 0 else "red"
        self.lbl_saldo.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")

    def delete_entry(self):
        rows = self.tb.selectionModel().selectedRows()
        if not rows: return
        id_val = int(self.tb.item(rows[0].row(), 0).text())
        if QMessageBox.question(self, "Confirmar", "Apagar lançamento?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_financeiro(id_val); self.load_data()

# --- 11. ABA: CONTROLE DE EPI ---
class EPITab(QWidget):
    def __init__(self, db, obra_id):
        super().__init__(); self.db = db; self.obra_id = obra_id
        main = QHBoxLayout()
        lw = QWidget(); ll = QVBoxLayout()
        ll.addWidget(QLabel("🦺 Histórico de Entregas"))
        self.tb = QTableWidget(0, 4); self.tb.setHorizontalHeaderLabels(["ID", "Data", "Funcionário", "Item (EPI)"])
        self.tb.setColumnHidden(0, True); self.tb.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        ll.addWidget(self.tb)
        btn_del = QPushButton("Desfazer Entrega"); btn_del.clicked.connect(self.delete_entry)
        ll.addWidget(btn_del); lw.setLayout(ll)
        rw = QWidget(); rw.setMaximumWidth(300); rl = QVBoxLayout()
        gb = QGroupBox("Nova Entrega"); gl = QGridLayout()
        self.dt = QDateEdit(); self.dt.setCalendarPopup(True); self.dt.setDate(QDate.currentDate()); self.dt.setDisplayFormat("dd/MM/yyyy")
        self.cb_func = QComboBox(); 
        self.txt_item = QLineEdit(); self.txt_item.setPlaceholderText("Item (Bota, Capacete...)")
        btn_add = QPushButton("Registrar Entrega"); btn_add.clicked.connect(self.add)
        gl.addWidget(QLabel("Data:"),0,0); gl.addWidget(self.dt,0,1)
        gl.addWidget(QLabel("Func:"),1,0); gl.addWidget(self.cb_func,1,1)
        gl.addWidget(QLabel("Item:"),2,0); gl.addWidget(self.txt_item,2,1)
        gl.addWidget(btn_add,3,0,1,2); gb.setLayout(gl)
        rl.addWidget(gb); rl.addStretch(); rw.setLayout(rl)
        main.addWidget(lw); main.addWidget(rw); self.setLayout(main); self.refresh_funcs(); self.load_data()
    def refresh_funcs(self):
        self.cb_func.clear()
        funcs = self.db.get_funcionarios(self.obra_id)
        for f in funcs: self.cb_func.addItem(f[2], userData=f[0])
    def add(self):
        if not self.txt_item.text(): return
        fid = self.cb_func.currentData()
        if fid is None: return
        self.db.add_epi(self.obra_id, fid, self.dt.date().toString("yyyy-MM-dd"), self.txt_item.text())
        self.txt_item.clear(); self.load_data()
    def load_data(self):
        rows = self.db.get_epi_historico(self.obra_id)
        self.tb.setRowCount(0)
        for r, row in enumerate(rows):
            self.tb.insertRow(r)
            self.tb.setItem(r, 0, QTableWidgetItem(str(row[0])))
            try: fmt = QDate.fromString(row[1], "yyyy-MM-dd").toString("dd/MM/yyyy")
            except: fmt = row[1]
            self.tb.setItem(r, 1, QTableWidgetItem(fmt))
            self.tb.setItem(r, 2, QTableWidgetItem(row[2]))
            self.tb.setItem(r, 3, QTableWidgetItem(row[3]))
    def delete_entry(self):
        rows = self.tb.selectionModel().selectedRows()
        if not rows: return
        id_val = int(self.tb.item(rows[0].row(), 0).text())
        if QMessageBox.question(self, "Confirmar", "Apagar registro?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_epi(id_val); self.load_data()

# --- 12. JANELA PRINCIPAL (MAIN WINDOW) ---
class ConstructionApp(QMainWindow):
    def __init__(self, db, obra_data):
        super().__init__()
        self.db = db; self.obra_id = obra_data[0]; self.obra_nome = obra_data[1]
        try: self.setWindowIcon(QIcon(resource_path("icone_obra.ico")))
        except: pass
        self.resize(1200, 800); self.setup_ui(); self.status = self.statusBar(); self.update_footer()
        self.load_window_settings()

    def setup_ui(self):
        self.setWindowTitle(f"Gestor de Obras - {self.obra_nome}")
        menu_bar = self.menuBar(); menu_bar.clear()
        file_menu = menu_bar.addMenu("☰ Menu")
        action_inactives = QAction("👥 Funcionários Inativos", self); action_inactives.triggered.connect(self.open_inactives); file_menu.addAction(action_inactives)
        file_menu.addSeparator()
        action_change = QAction("🔄 Trocar Obra", self); action_change.triggered.connect(self.trocar_obra)
        file_menu.addAction(action_change)
        action_exit = QAction("❌ Sair", self); action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        self.tabs = QTabWidget()
        
        # Instanciando as abas (TODAS DEFINIDAS ANTES)
        self.tab_calc = MaterialCalculator()
        self.tab_stock = StockControl(self.db, self.obra_id)
        self.tab_employees = EmployeeManager(self.db, self.obra_id)
        self.tab_reports = ReportTab(self.db, self.obra_id)
        self.tab_diary = DiaryTab(self.db, self.obra_id)
        self.tab_finance = FinancialTab(self.db, self.obra_id)
        self.tab_epi = EPITab(self.db, self.obra_id)
        
        # Adicionando ao TabWidget
        self.tabs.addTab(self.tab_calc, "🧮 Calculadora")
        self.tabs.addTab(self.tab_diary, "📘 Diário de Obra")
        self.tabs.addTab(self.tab_finance, "💰 Financeiro (Caixa)")
        self.tabs.addTab(self.tab_stock, "📦 Estoque")
        self.tabs.addTab(self.tab_employees, "👷 Funcionários")
        self.tabs.addTab(self.tab_epi, "🦺 Controle de EPI")
        self.tabs.addTab(self.tab_reports, "📅 Relatórios")
        
        self.setCentralWidget(self.tabs)

    def open_inactives(self):
        dialog = InactiveEmployeesDialog(self.db, self.obra_id); dialog.exec(); self.tab_employees.ld()

    def update_footer(self):
        self.status.clearMessage()
        for child in self.status.findChildren(QLabel): self.status.removeWidget(child)
        credits = QLabel(f"Obra Ativa: {self.obra_nome} | Desenvolvido por Amizael Alves | amizael@gmail.com | ©2026")
        credits.setStyleSheet("color: #444; font-weight: bold; margin-right: 15px;")
        self.status.addPermanentWidget(credits)

    def trocar_obra(self):
        selector = ProjectSelector(self.db)
        if selector.exec() == QDialog.Accepted:
            self.save_window_settings() 
            nova_obra = selector.selected_obra
            self.obra_id = nova_obra[0]; self.obra_nome = nova_obra[1]
            self.setup_ui(); self.update_footer(); self.load_window_settings()

    def closeEvent(self, event):
        self.save_window_settings()
        event.accept()

    def save_window_settings(self):
        settings = QSettings("MiizaSoft", "GestorObras")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        self.tab_stock.save_table_state()
        self.tab_employees.save_table_state()
        self.tab_reports.save_table_state()

    def load_window_settings(self):
        settings = QSettings("MiizaSoft", "GestorObras")
        if geo := settings.value("geometry"): self.restoreGeometry(geo)
        if state := settings.value("windowState"): self.restoreState(state)
        self.tab_stock.load_table_state()
        self.tab_employees.load_table_state()
        self.tab_reports.load_table_state()

# --- 13. EXECUÇÃO DO PROGRAMA ---
if __name__ == "__main__":
    with contextlib.suppress(Exception):
        myappid = 'miiza.gestor.obras.v26_3'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    try: app.setWindowIcon(QIcon(resource_path("icone_obra.ico")))
    except: pass
    
    db = Database()
    selector = ProjectSelector(db)
    
    if selector.exec() == QDialog.Accepted:
        obra_selecionada = selector.selected_obra
        window = ConstructionApp(db, obra_selecionada)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)