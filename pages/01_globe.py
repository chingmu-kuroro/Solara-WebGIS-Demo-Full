import solara
import leafmap.maplibregl as leafmap


def create_map():

    m = leafmap.Map(
        style="dark-matter",
        #projection="globe",
        center=[121.5654, 25.0330], # 台北 101
        zoom=20,
        pitch=60,
        bearing=-17,
        height="750px",
        sidebar_visible=True,
    )
    m.add_basemap("Satellite", visible=False)
    m.add_overture_3d_buildings(template="simple")

    lines_url = "https://drive.google.com/uc?id=1RwHIhfEINPFRYUCToMJzaOIEXLPNmZjX"
    m.add_geojson(lines_url, name="Lines")

    points_url = "https://drive.google.com/uc?id=1hmx20mj3XhqF4MViL03WWUdNN4bYlHZL"
    m.add_geojson(points_url, name="Points")

    return m


@solara.component
def Page():
    m = create_map()
    return m.to_solara()

