from matplotlib import pyplot as plt
from matplotlib.patches import Arc
import numpy as np

from planning.utils import dist, transform_polar, v2v_angle


class Circle:
    """
    Class to represent circles.
    Stores the radius and center of the circle.

    """

    def __init__(self, r, center):
        self.r = r
        self.center = center

    def get_r(self):
        return self.r

    def get_center(self):
        return self.center

class Node:
    """
    Class that represents a node in the graph. Stores the circle the node is on and its (x, y) postion.

    """

    def __init__(self, circle, position):
        self.circle = circle
        self.position = position

    def get_circle(self):
        return self.circle

    def get_position(self):
        return self.position

    def get_x(self):
        return self.position[0]

    def get_y(self):
        return self.position[1]

    def __lt__(self, other):
        """
        Implements the less than operator for nodes.
        NOTE: This is used to compare nodes in the priority queue.
        If two nodes have the same priority, the one with the lower id is considered to be less than the other.
        TODO: Bit sus?
        """
        return id(self) < id(other)


class Edge:
    """
    Class that represents an edge in the graph. This is a line segment or arc between two nodes.
    NOTE: Surfing edges are line segments, while hugging edges are arcs.
    """

    def __init__(self, first, second, is_surfing):
        self.first = first
        self.second = second

        self.surfing = is_surfing

    def get_first(self):
        return self.first

    def get_second(self):
        return self.second

    def is_surfing(self):
        return self.surfing

    def check_equivalence(self, other):
        """
        Checks if two edges are equivalent.
        Two edges are equivalent if they have the same nodes in the same order.

        """
        return (self.get_first() == other.get_first() and self.get_second() == other.get_second()) or (self.get_first() == other.get_second() and self.get_second() == other.get_first())

class Graph:
    def __init__(self, circles):
        self.nodes = {}
        self.circles = {}

        self.surfing_edges = []
        self.hugging_edges = []

        # Add the circles to the graph
        for circle in circles:
            for other_circle in circles:
                if circle == other_circle:
                    continue
                
                # Add internal and external bitangents btetween circles
                self.add_internal_bitangets(other_circle, circle)
                self.add_external_bitangets(other_circle, circle)

        # Add hugging edges
        self.add_hugging_edges()

        # Clean up the sufing edge intersections
        self.clean_surfing_edges()

    def get_nodes(self):
        return self.nodes
    
    def get_circles(self):
        return self.circles
    
    def get_edges(self):
        return self.surfing_edges + self.hugging_edges

    def clear(self):
        self.nodes.clear()
        self.circles.clear()

        self.surfing_edges.clear()
        self.hugging_edges.clear()

    def get_neighbors(self, node):
        """
        Returns the neighbors of a node on the graph.
        Returns a list of tuples of the form (node, edge).

        """
        neighbors = []

        for edge in self.get_edges():
            if edge.get_first() == node:
                neighbors.append((edge.get_second(), edge))
            elif edge.get_second() == node:
                neighbors.append((edge.get_first(), edge))

        return neighbors

    def add_node(self, node):
        circle = node.get_circle()
        self.circles[id(circle)] = circle
        self.nodes[id(node)] = node

    def add_edge(self, edge):
        # If the edge is hugging, automatically append it
        # Or, if the edge is surfing, check if the edge intersects any of the circles in the graph
        if not edge.is_surfing():
            self.hugging_edges.append(edge)
        else:
            self.surfing_edges.append(edge)

    def clean_surfing_edges(self):
        """
        Removes all edges that intersect any of the circles in the graph.

        """
        new_surfing_edges = self.surfing_edges.copy()
        for edge in self.surfing_edges:
            if self.check_intersection(edge):
                new_surfing_edges.remove(edge)
        
        self.surfing_edges = new_surfing_edges


    def check_intersection(self, edge):
        """
        Checks if an edge intersects any of the circles in the graph.

        """
        circles_to_ignore = [edge.get_first().get_circle(), edge.get_second().get_circle()]

        for circle in self.circles.values():
            if circle in circles_to_ignore:
                continue

            if self.check_circle_intersection(circle, edge):
                return True

        return False

    def add_point(self, node):
        """
        Inserts a point (circle with raidus 0) into the graph.
        NOTE: This updates the surfing and hugging edges.

        """
        # Add the node and its circle to the graph
        self.add_node(node)

        # Add external and internal bigtangents to the point
        for other_circle in self.circles.values():
            if other_circle == node.get_circle():
                continue
                
            # We only need to add internal bitangents for points
            self.add_tangents(node, other_circle)

        # Recalculate the hugging edges
        self.clean_surfing_edges()
        self.add_hugging_edges() # TODO: Optimize this

        return node

    def add_tangents(self, point_node, circle):
        """
        Generates the tangents between a point and a circle
        
        """
        # Unpack the circle center and radius
        A = point_node.get_position()
        B = circle.get_center()
        r = circle.get_r()

        # First check if the second circle is a point
        if r == 0:
            # If so, connect the two nodes
            # Find the node on the circle
            for node in self.nodes.values():
                if node.get_circle() == circle:
                    circle_node = node
                    break
                    
            # Generate the edge
            edge = Edge(point_node, circle_node, True)
            
            # Check if the edge already exists
            for other_edge in self.surfing_edges:
                if edge.check_equivalence(other_edge):
                    return
            
            # Add the edge
            self.add_edge(edge)
            return

    
        # Calculate the internal bitangent angle, theta
        d = dist(A, B)
        theta = np.arccos(r / d)

        # Calclate the AB and BA angles
        angle_BA = v2v_angle(B, A)

        # Calculate the internal bitanget points: E and F
        # Nodes on circle : E and F
        E = transform_polar(B, r, angle_BA - theta)
        F = transform_polar(B, r, angle_BA + theta)

        # Create nodes
        E_node = Node(circle, E)
        F_node = Node(circle, F)

        # Add nodes to graph
        self.add_node(E_node)
        self.add_node(F_node)

        # Generate the internal bitangent edges
        self.add_edge(Edge(point_node, E_node, True))
        self.add_edge(Edge(point_node, F_node, True))
        

    def add_internal_bitangets(self, circle1, circle2):
        """
        Generates the internal bitangents between two circles.

        NOTE: circle1 is A and circle2 is B.
        """
        # Unpack the circle centers and radii
        A = circle1.get_center()
        B = circle2.get_center()

        r1 = circle1.get_r()
        r2 = circle2.get_r()

        # Calculate the internal bitangent angle, theta
        d = dist(A, B)
        theta = np.arccos((r1 + r2) / d)

        # Calclate the AB and BA angles
        angle_AB = v2v_angle(A, B)
        angle_BA = v2v_angle(B, A)

        # Calculate the internal bitanget points: C, D, E and F
        # Nodes on circle 1: C and D
        C = transform_polar(A, r1, angle_AB + theta)
        D = transform_polar(A, r1, angle_AB - theta)

        # Nodes on circle 2: E and F
        E = transform_polar(B, r2, angle_BA - theta)
        F = transform_polar(B, r2, angle_BA + theta)

        # Create nodes
        C_node = Node(circle1, C)
        D_node = Node(circle1, D)

        E_node = Node(circle2, E)
        F_node = Node(circle2, F)

        # Add nodes to graph
        self.add_node(C_node)
        self.add_node(D_node)

        self.add_node(E_node)
        self.add_node(F_node)

        # Generate the internal bitangent edges
        self.add_edge(Edge(D_node, E_node, True))
        self.add_edge(Edge(C_node, F_node, True))

    def add_external_bitangets(self, circle1, circle2):
        """
        Generates the external bitangents between two circles.

        NOTE: circle1 is A and circle2 is B.
        """
        # Unpack the circle centers and radii
        A = circle1.get_center()
        B = circle2.get_center()

        r1 = circle1.get_r()
        r2 = circle2.get_r()

        # Calculate the internal bitangent angle, theta
        d = dist(A, B)
        theta = np.arccos(abs(r1 - r2) / d)

        # Calclate the AB and BA angles
        angle_AB = v2v_angle(A, B)
        angle_BA = v2v_angle(B, A)

        # Calculate the internal bitanget points: C, D, E and F
        # Nodes on circle 1: C and D
        C = transform_polar(A, r1, angle_AB + theta)
        D = transform_polar(A, r1, angle_AB - theta)

        # Nodes on circle 2: E and F
        # NOTE: We use "angle AB" instead of BA because theta is measured from AB. BA is opposite to AB so we need to add pi to it.
        # angle_AB = angle_BA + np.pi
        E = transform_polar(B, r2, (angle_BA + np.pi) - theta)
        F = transform_polar(B, r2, (angle_BA + np.pi) + theta)

        # Create nodes
        C_node = Node(circle1, C)
        D_node = Node(circle1, D)

        E_node = Node(circle2, E)
        F_node = Node(circle2, F)

        # Add nodes to graph
        self.add_node(C_node)
        self.add_node(D_node)

        self.add_node(E_node)
        self.add_node(F_node)
        
        # Generate external bitangent edges
        self.add_edge(Edge(D_node, E_node, True))
        self.add_edge(Edge(C_node, F_node, True))

    def add_hugging_edges(self):
        """
        Updates the hugging edges in the graph.
        """
        # Remove all the hugging edges
        self.hugging_edges = []

        # Sort the nodes by circle
        nodes_by_circle = {}
        for node in self.nodes.values():
            circle = node.get_circle()
            if circle.get_r() == 0:
                # Ignore nodes on a circle with zero radius
                continue

            if circle not in nodes_by_circle:
                nodes_by_circle[circle] = []

            nodes_by_circle[circle].append(node)

        # Add the hugging edges
        for nodes in nodes_by_circle.values():
            for i in range(len(nodes)):
                # Connect the nodes in a circle
                n1 = nodes[i] # Current node
                n2 = nodes[(i + 1) % len(nodes)] # Next node (wraps around to the first node when the current node is the last node)

                self.add_edge(Edge(n1, n2, False))    

    def plot_graph(self, axs, simplify=True):
        """
        Plots the graph on the given axes.
        """
        # Set square aspect ratio
        axs.set_aspect("equal")

        # Plot the circles
        for circle in self.circles.values():
            axs.add_patch(plt.Circle(circle.get_center(), circle.get_r(), fill=False))

        if not simplify:
            # Plot the surfing edge lines
            # count = 0
            for edge in self.surfing_edges:
                first = edge.get_first()
                second = edge.get_second()

                axs.plot([first.get_x(), second.get_x()], [first.get_y(), second.get_y()], "b-")

                # # Label the surfing edges
                # axs.text((first.get_x() + second.get_x()) / 2, (first.get_y() + second.get_y()) / 2, str(count), color="b")
                # count += 1

            # Plot the hugging edge arcs
            for edge in self.hugging_edges:
                first = edge.get_first()
                second = edge.get_second()

                arc_center = first.get_circle().get_center()
                arc_radius = first.get_circle().get_r()

                arc_start = v2v_angle(arc_center, first.get_position())
                arc_end = v2v_angle(arc_center, second.get_position())

                axs.add_patch(Arc(arc_center, 2 * arc_radius, 2 * arc_radius, theta1=np.rad2deg(arc_start), theta2=np.rad2deg(arc_end), color="g"))

            # Plot the nodes
            for node in self.nodes.values():
                axs.plot(node.get_x(), node.get_y(), "ro")

    @staticmethod
    def check_circle_intersection(circle, edge):
        """
        Checks if the given edge intersects the given circle.
        Returns True if the edge intersects the circle, False otherwise.

        """
        # Unpack the circle parameters
        center = circle.get_center()
        r = circle.get_r()

        pos1 = edge.get_first().get_position()
        pos2 = edge.get_second().get_position()

        # Calculate the distance between the edge and the circle center
        # Creates a parallelogram where the edge is the base and the circle lies on one of the corners with:
        # 1. A vector from the start of the edge to the end of the edge
        # 2. A vector from the start of the edge to the circle center
        # So, the distance is the height of the parallelogram and the length of the edge is the base
        # The area of the parallelogram (b * h) is the norm of the cross product of the two vectors

        # We also need to determine if the point is over the edge of the line segment or not
        # We can do this by taking the dot product of a vector from the start to the center of the circle and a vector from the start to the end
        # If the dot product is negative, the point is on the other side of the line segment
        # We can do the same for the end of the line segment taking the dot product of a vector from the end to the center of the circle and a vector from the end to the start
        # If the dot product is negative, the point is on the other side of the line segment
        # If either dot product is negative, we set the distannce equal to the distance between the circle center and the closest point on the line segment (either the start or the end)
        
        # Check if circle is over the edge:
        # If np.dot(center - pos1, pos2 - pos1) < 0 then d = dist(center, pos1)
        # If np.dot(center - pos2, pos1 - pos2) < 0 then d = dist(center, pos2)
        if (np.dot(center - pos1, pos2 - pos1) < 0):
            d = dist(center, pos1)
        elif (np.dot(center - pos2, pos1 - pos2) < 0):
            d = dist(center, pos2)
        else:
            # Check the distance from the circle to the edge
            # A = b * h
            # b = |pos2 - pos1|
            # A = |(pos2 - pos1) x (center - pos1)|
            # h = A / b
            # h = |(pos2 - pos1) x (center - pos1)| / |pos2 - pos1|
            d = np.linalg.norm(np.cross(pos2 - pos1, center - pos1)) / dist(pos2, pos1)

        # Check if the edge intersects the circle
        if (d <= r):
            return True
        else:
            return False

if __name__ == "__main__":
    # Testing Two Circles
    # circle1 = Circle(1, np.array([0, 0]))
    # circle2 = Circle(1, np.array([-3, -3]))

    # graph = Graph()
    # graph.add_internal_bitangets(circle1, circle2)
    # graph.add_external_bitangets(circle1, circle2)

    # fig, axs = plt.subplots()
    # graph.plot_graph(axs)

    # Testing Grid of Circles
    graph = Graph([])

    grid_dims = np.array([8, 4])
    grid_spacing = 1

    circle_radius = 0.1

    # Generate grid of circles
    circles = []
    for i in range(0, grid_dims[0]):
        for j in range(0, grid_dims[1]):
            # Generate circle
            i_circle = Circle(circle_radius, np.array([i * grid_spacing, j * grid_spacing]))

            # Add internal and external bitangents between all circles
            for circle in circles:
                graph.add_internal_bitangets(i_circle, circle)
                graph.add_external_bitangets(i_circle, circle)

            # Store circle
            circles.append(i_circle)

    graph.add_hugging_edges()

    print("Generated Graph!")

    fig, axs = plt.subplots()
    graph.plot_graph(axs)

    plt.show()
