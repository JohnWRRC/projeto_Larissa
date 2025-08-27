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
# 1) GERAR LINHAS A PARTIR DOS PONTOS
layer = QgsVectorLayer(entrada_pontos, "pontos_lote", "ogr")
if not layer.isValid():
    raise Exception("Não consegui abrir o shapefile de entrada.")

if layer.wkbType() != QgsWkbTypes.Point:
    raise Exception("A camada de entrada deve ser do tipo Ponto.")

if "direct" not in [f.name() for f in layer.fields()]:
    raise Exception("O shapefile de pontos precisa ter o campo 'direct'.")

mapa_direct = {
    "1": "Frente",
    "2": "Lateral Esquerda",
    "3": "Fundo",
    "4": "Lateral Direita",
    "5": "Fechamento"  # será ignorado
}

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

pontos = [feat for feat in layer.getFeatures()]
pontos.sort(key=lambda f: f.id())

novas_feats = []

# 2) CARREGAR POLIGONOS PARA CONSULTA DE GEO LINK
polygons_layer = QgsVectorLayer(poligonos_shp, "poligonos", "ogr")
if not polygons_layer.isValid():
    raise Exception("Erro ao carregar o shapefile de poligonos.")

index = QgsSpatialIndex(polygons_layer.getFeatures())

# 3) CRIAR LINHAS COM GEO LINK
lote_atual = []
for i in range(len(pontos)-1):
    p1 = pontos[i]
    p2 = pontos[i+1]

    direct_val = str(p1["direct"])
    chave = re.match(r"\d+", direct_val)
    if chave:
        chave = chave.group()
    else:
        continue

    if chave not in mapa_direct or chave == "5":
        continue

    posicao = mapa_direct[chave]

    x1, y1 = p1.geometry().asPoint()
    x2, y2 = p2.geometry().asPoint()
    comprimento = math.hypot(x2 - x1, y2 - y1)

    linha = QgsFeature(out_layer.fields())
    linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1, y1), QgsPointXY(x2, y2)]))
    linha.setAttributes([direct_val, posicao, comprimento, None])  # geolink vai ser preenchido depois
    lote_atual.append(linha)

    # quando chega na lateral direita, lote completo
    if posicao == "Lateral Direita":
        # calcular centroid do lote
        coords = []
        for lf in lote_atual:
            geom = lf.geometry()
            if geom.isMultipart():
                for part in geom.asMultiPolyline():
                    coords.extend(part)
            else:
                coords.extend(geom.asPolyline())
        centroid_geom = QgsGeometry.fromPolygonXY([coords]).centroid()
        candidate_ids = index.intersects(centroid_geom.boundingBox())
        geolink_value = None
        for pid in candidate_ids:
            poly_feat = polygons_layer.getFeature(pid)
            if centroid_geom.intersects(poly_feat.geometry()):
                geolink_value = poly_feat["geolink"]
                break
        # atribuir geolink a todas as linhas do lote
        for lf in lote_atual:
            lf.setAttribute("geolink", geolink_value)
            novas_feats.append(lf)

        lote_atual = []

# adicionar todas as linhas na camada de saída
pr.addFeatures(novas_feats)
out_layer.updateExtents()

QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_linhas, "utf-8", out_layer.crs(), "ESRI Shapefile"
)
QgsProject.instance().addMapLayer(out_layer)

print(f"Shapefile de linhas com métricas e geolink gerado: {saida_linhas}")
