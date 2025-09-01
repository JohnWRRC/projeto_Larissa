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
pontos = [feat for feat in layer.getFeatures()]
pontos.sort(key=lambda f: f.id())

novas_feats = []

# --------------------------
# 2) CARREGAR POLIGONOS PARA GEO LINK
polygons_layer = QgsVectorLayer(poligonos_shp, "poligonos", "ogr")
if not polygons_layer.isValid():
    raise Exception("Erro ao carregar o shapefile de poligonos.")

index = QgsSpatialIndex(polygons_layer.getFeatures())

# --------------------------
# Função para definir posicao
def classificar_conexao(p1_val, p2_val):
    lateral = {
        "1": "Frente",
        "2": "Lateral direita",
        "3": "Fundo",
        "4": "Lateral esquerda"
    }

    # Normaliza valores maiúsculos
    p1_val = str(p1_val).upper()
    p2_val = str(p2_val).upper()

    # Se algum ponto for X, é LinhaApoio
    if "X" in [p1_val, p2_val]:
        return "LinhaApoio"

    # Se for ramificação (ex: 2a…2f), pegamos o número principal
    match1 = re.match(r"(\d)", p1_val)
    match2 = re.match(r"(\d)", p2_val)
    if match1 and match2:
        n1, n2 = match1.group(1), match2.group(1)
        # Se p1 e p2 são número principal ou ramificação do mesmo número → mesma lateral
        if n1 == n2:
            return lateral[n1]
        # Se é a última ramificação → próximo número
        if p1_val.endswith("f") and int(n1) % 4 + 1 == int(n2):
            return lateral[n1]
        # Se números diferentes → segue a direção do número inicial
        if n1 != n2:
            return lateral[n1]
    return "Desconhecido"

# --------------------------
# 3) CRIAR LINHAS COM GEO LINK
lote_atual = []
for i in range(len(pontos) - 1):
    p1 = pontos[i]
    p2 = pontos[i + 1]

    p1_val = str(p1["direct"]).upper()
    p2_val = str(p2["direct"]).upper()

    posicao = classificar_conexao(p1_val, p2_val)

    # Criar linha entre p1 e p2
    x1, y1 = p1.geometry().asPoint()
    x2, y2 = p2.geometry().asPoint()
    comprimento = math.hypot(x2 - x1, y2 - y1)

    linha = QgsFeature(out_layer.fields())
    linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1, y1), QgsPointXY(x2, y2)]))
    linha.setAttributes([f"{p1_val}->{p2_val}", posicao, comprimento, None])
    lote_atual.append(linha)

    # Quando chega em lateral direita/esquerda/fundo → fecha lote
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
# 4) REMOVER SOBREPOSIÇÕES EXATAS
final_feats = []
seen = set()
for feat in novas_feats:
    wkt = feat.geometry().asWkt()
    if wkt not in seen:
        seen.add(wkt)
        final_feats.append(feat)

# --------------------------
# 5) ADICIONAR NA CAMADA DE SAÍDA
pr.addFeatures(final_feats)
out_layer.updateExtents()

QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_linhas, "utf-8", out_layer.crs(), "ESRI Shapefile"
)
QgsProject.instance().addMapLayer(out_layer)

print(f"Shapefile de linhas com métricas e geolink gerado: {saida_linhas}")
