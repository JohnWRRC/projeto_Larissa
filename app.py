from qgis.core import (
    QgsVectorLayer, QgsWkbTypes, QgsFeature, QgsGeometry, QgsField, QgsVectorFileWriter, QgsProject, QgsPointXY
)
from PyQt6.QtCore import QVariant
import math

# === CONFIGURAÇÃO ===
entrada_shp = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_shp.shp"     # <-- shapefile dos lotes
saida_shp   = r"D:/data/_____dados/consultorias/Larissa/amostra_lotes_shp_laterais.shp"

# carrega camada
layer = QgsVectorLayer(entrada_shp, "lotes", "ogr")
if not layer.isValid():
    raise Exception("Não consegui abrir o shapefile de entrada.")

if layer.wkbType() not in [QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon]:
    raise Exception("A camada selecionada não é poligonal.")

# tenta achar campo ID
id_field = None
for cand in ["id","ID","Id","lote","Lote","LOT","COD","CODIGO"]:
    if cand in [f.name() for f in layer.fields()]:
        id_field = cand
        break

# cria camada de saída (linhas)
crs = layer.crs().toWkt()
out_layer = QgsVectorLayer("LineString?crs=" + crs, "laterais_lotes", "memory")
pr = out_layer.dataProvider()
pr.addAttributes([
    QgsField("id_lote", QVariant.String),
    QgsField("comprimento", QVariant.Double),
    QgsField("posicao", QVariant.String)
])
out_layer.updateFields()

def classificar_posicao(x1,y1,x2,y2):
    dx = x2 - x1
    dy = y2 - y1
    ang = math.degrees(math.atan2(dy, dx))  # ângulo em graus (-180 a 180)
    if -45 <= ang <= 45:
        return "Frente" if y1 < y2 else "Fundo"
    elif 135 <= ang <= 180 or -180 <= ang <= -135:
        return "Fundo" if y1 < y2 else "Frente"
    elif 45 < ang < 135:
        return "Direita"
    else:
        return "Esquerda"

novas_feats = []

for f_idx, feat in enumerate(layer.getFeatures()):
    lote_id = feat[id_field] if id_field else f"L{f_idx+1}"
    geom = feat.geometry()
    if geom.isMultipart():
        polys = geom.asMultiPolygon()
    else:
        polys = [geom.asPolygon()]
    for part in polys:
        if not part:
            continue
        exterior = part[0]
        for i in range(len(exterior)-1):
            x1,y1 = exterior[i]
            x2,y2 = exterior[i+1]
            comprimento = math.hypot(x2-x1, y2-y1)
            pos = classificar_posicao(x1,y1,x2,y2)

            linha = QgsFeature(out_layer.fields())
            linha.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x1,y1), QgsPointXY(x2,y2)]))
            linha.setAttributes([str(lote_id), comprimento, pos])
            novas_feats.append(linha)

pr.addFeatures(novas_feats)
out_layer.updateExtents()

# salva em shapefile
_writer = QgsVectorFileWriter.writeAsVectorFormat(
    out_layer, saida_shp, "utf-8", out_layer.crs(), "ESRI Shapefile"
)

# adiciona no projeto QGIS
QgsProject.instance().addMapLayer(out_layer)
print(f"Arquivo gerado: {saida_shp}")
