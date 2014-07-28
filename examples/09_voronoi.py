import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi


# source: https://gist.github.com/pv/8036995
from geoplotlib.layers import HotspotManager


def voronoi_finite_polygons_2d(vor, radius=None):
    """
    Reconstruct infinite voronoi regions in a 2D diagram to finite
    regions.

    Parameters
    ----------
    vor : Voronoi
        Input diagram
    radius : float, optional
        Distance to 'points at infinity'.

    Returns
    -------
    regions : list of tuples
        Indices of vertices in each revised Voronoi regions.
    vertices : list of tuples
        Coordinates for revised Voronoi vertices. Same as coordinates
        of input vertices, with 'points at infinity' appended to the
        end.

    """

    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max()*2

    # Construct a map containing all ridges for a given point
    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    # Reconstruct infinite regions
    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]

        if all(v >= 0 for v in vertices):
            # finite region
            new_regions.append(vertices)
            continue

        # reconstruct a non-finite region
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                # finite ridge: already in the region
                continue

            # Compute the missing endpoint of an infinite ridge

            t = vor.points[p2] - vor.points[p1] # tangent
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])  # normal

            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius

            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        # sort region counterclockwise
        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:,1] - c[1], vs[:,0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]

        # finish
        new_regions.append(new_region.tolist())

    return new_regions, np.asarray(new_vertices)


import sys,os
sys.path.append(os.path.realpath('..'))

from geoplotlib.core import BatchPainter
import geoplotlib
from geoplotlib.utils import read_csv


class VoronoiLayer():

    def __init__(self, data, f_tooltip=None):
        self.data = data
        self.f_tooltip = f_tooltip


    def invalidate(self, proj):
        x, y = proj.lonlat_to_screen(self.data['lon'], self.data['lat'])
        points = np.vstack((x,y)).T
        vor = Voronoi(points)

        regions, vertices = voronoi_finite_polygons_2d(vor)

        self.hotspots = HotspotManager()
        self.painter = BatchPainter()
        self.painter.set_color([255,0,0])
        for idx, region in enumerate(regions):
            polygon = vertices[region]
            self.painter.linestrip(polygon[:,0], polygon[:,1], width=5, closed=True)
            if self.f_tooltip:
                record = {k: self.data[k][idx] for k in self.data.keys()}
                self.hotspots.add_poly(polygon[:,0], polygon[:,1], self.f_tooltip(record))
        self.painter.set_color([0,0,255])
        self.painter.points(x, y)


    def draw(self, mouse_x, mouse_y, ui_manager):
        self.painter.batch_draw()
        picked = self.hotspots.pick(mouse_x, mouse_y)
        if picked:
            ui_manager.tooltip(picked)


data = read_csv('/Users/ancu/Dropbox/phd/code-projects/geoplotlib/examples/data/s-tog.csv')
geoplotlib.add_layer(VoronoiLayer(data, f_tooltip=lambda r: r['name']))
geoplotlib.show()