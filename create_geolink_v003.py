# Autor: John Wesley Ribeiro
from qgis.core import (
    QgsVectorLayer, QgsWkbTypes, QgsFeature, QgsGeometry,
    QgsField, QgsVectorFileWriter, QgsProject, QgsPointXY,
    QgsSpatialIndex
)
from PyQt6.QtCore import QVariant
import math
import re

# === CONFIGURAÇÃO ===
entrada_pontos = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_pontos.shp"
poligonos_shp = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_shp.shp"
saida_linhas = r"D:/data/_____dados/consultorias/Larissa/laterais_com_geolink.shp"

# --------------------------
# 1) CARREGAR CAMADA DE PONTOS
layer = QgsVectorLayer(entrada_pontos, "pontos_lote", "ogr")
if not layer.isValid():
    raise Exception("Não consegui abrir o shapefile de entrada.")
if layer.wkbType() != QgsWkbTypes.Point:
    raise Exception("A camada de entrada deve ser do tipo Ponto.")
if "direct" not in [f.name() for f in layer.fields()]:
    raise Exception("O shapefile de pontos precisa ter o campo 'direct'.")

# Mapeamento das posições para números principais
mapa_direct = {
    "1": "Frente",
    "2": "Lateral direita",
    "3": "Fundo",
    "4": "Lateral esquerda",
    "5": "Fechamento"  # será ignorado
}

# Criar camada de saída em memória
crs = layer.crs().toWkt()
out_layer = QgsVectorLayer("LineString?crs=" + crs, "laterais_lotes", "memory")
pr = out_layer.dataProvider()
pr.addAttributes([
    QgsField("direct", QVariant.String),
    QgsField("posicao", QVariant.String),
    QgsField("comprimento", QVariant.Double),
    QgsField("geolink", QVariant.String)
])
out_layer.updateFields()

# Ordenar pontos por ID
pontos = sorted([feat for feat in layer.getFeatures()], key=lambda f: f.id())

novas_feats = []

# --------------------------
# 2) CARREGAR POLIGONOS PARA GEO LINK
polygons_layer = QgsVectorLayer(poligonos_shp, "poligonos", "ogr")
if not polygons_layer.isValid():
    raise Exception("Erro ao carregar o shapefile de poligonos.")
index = QgsSpatialIndex(polygons_layer.getFeatures())

# --------------------------
# 3) FUNÇÃO PARA CLASSIFICAR CONEXÃO ENTRE DOIS PONTOS
def classificar_conexao(p1_val, p2_val, lateral_anterior=None):
    """
    Classifica a lateral da linha entre p1 e p2 seguindo a lógica:
    - Ramificações herdam lateral do número principal
    - X → sempre LinhaApoio se for destino de número ou ramificação
    - X → número → herda lateral do ponto anterior
    - Sequência normal de números principais segue mapa_direct
    """
    p1_val = str(p1_val).upper()
    p2_val = str(p2_val).upper()

    # Caso destino seja X e venha de número ou ramificação → LinhaApoio
    if p2_val == "X":
        return "LinhaApoio"

    # Caso origem seja X → herda lateral do ponto anterior
    if p1_val == "X" and lateral_anterior is not None:
        return lateral_anterior

    # Se ambos são números ou ramificações, extrair número principal
    match1 = re.match(r"(\d)", p1_val)
    match2 = re.match(r"(\d)", p2_val)
    if match1 and match2:
        n1, n2 = match1.group(1), match2.group(1)

        # Mesmo número principal → mesma lateral
        if n1 == n2:
            return mapa_direct[n1]

        # Última ramificação f → próximo número → herda lateral do número principal
        if p1_val.endswith("F") and int(n1) % 4 + 1 == int(n2):
            return mapa_direct[n1]

        # Número diferente → lateral do ponto de origem
        return mapa_direct[n1]

    # Se algum valor não for reconhecido
    return "Desconhecido"

# --------------------------
# 4) CRIAR LINHAS COM GEO LINK
lote_atual = []
lateral_atual = None  # guarda a lateral para herança de X

for i in range(len(pontos) - 1):
    p1 = pontos[i]
    p2 = pontos[i + 1]

    p1_val = str(p1["direct"]).upper()
    p2_val = str(p2["direct"]).upper()

    # Classifica conexão
    posicao = classificar_conexao(p1_val, p2_val, lateral_atual)

    # Atualiza lateral_atual para herança futura (X → próximo)
    if posicao != "LinhaApoio":
        lateral_atual = posicao

    # Criar linha entre p1 e p2
    x1, y1 = p1.geometry().asPoint()
    x2, y2 = p2.geometry().asPoint()
    comprimento = math.hypot(x2 - x1, y2 - y1)

    linha = QgsFeature(out_layer.fields())
    linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1, y1), QgsPointXY(x2, y2)]))
    linha.setAttributes([f"{p1_val}->{p2_val}", posicao, comprimento, None])
    lote_atual.append(linha)

    # Fechar lote se posição é uma lateral "principal"
    if posicao in ["Lateral direita", "Lateral esquerda", "Fundo", "Frente"]:
        coords = []
        for lf in lote_atual:
            geom = lf.geometry()
            if geom.isMultipart():
                for part in geom.asMultiPolyline():
                    coords.extend(part)
            else:
                coords.extend(geom.asPolyline())

        # Calcular centróide
        centroid_geom = QgsGeometry.fromPolylineXY(coords).centroid()

        # Buscar polígono correspondente
        candidate_ids = index.intersects(centroid_geom.boundingBox())
        geolink_value = None
        for pid in candidate_ids:
            poly_feat = polygons_layer.getFeature(pid)
            if centroid_geom.intersects(poly_feat.geometry()):
                geolink_value = poly_feat["geolink"]
                break

        # Atribuir geolink às linhas do lote
        for lf in lote_atual:
            lf.setAttribute("geolink", geolink_value if geolink_value else "N/A")
            novas_feats.append(lf)

        # Reiniciar lote
        lote_atual = []

# --------------------------
# 5) REMOVER SOBREPOSIÇÕES EXATAS
final_feats = []
seen = set()
for feat in novas_feats:
    wkt = feat.geometry().asWkt()
    if wkt not in seen:
        seen.add(wkt)
        final_feats.append(feat)

# --------------------------
# 6) ADICIONAR NA CAMADA DE SAÍDA
pr.addFeatures(final_feats)
out_layer.updateExtents()

QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_linhas, "utf-8", out_layer.crs(), "ESRI Shapefile"
)
QgsProject.instance().addMapLayer(out_layer)

print(f"Shapefile de linhas com métricas e geolink gerado: {saida_linhas}")
