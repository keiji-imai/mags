from enum import Enum
import numpy as np
from matplotlib import pyplot as plt
from klipper_interface import Klipper

from planning.astar import Astar
from planning.board import PhysicalBoard

from stockfish import Stockfish

from planning.utils import v2v_angle, zero_to_2pi


class MoveManager():
    """
    A class that hooks into stockfish to manage the path planning and board state handling for the robot.

    """

    def __init__(self, board: PhysicalBoard, astar: Astar, stockfish: Stockfish):
        self.board = board
        self.astar = astar

        self.stockfish = stockfish

    def respond(self, plotting_axs=None):
        """
        Respond to the current board state.

        """
        # Get the current board state
        fen = self.board.get_fen()

        # Get the best move UCI from stockfish
        self.stockfish.set_fen_position(fen)
        best_move = self.stockfish.get_best_move()

        # Get the start and end squares
        # Read the UCI string from the start to account for promotion
        start_square = best_move[:2]
        end_square = best_move[2:4]

        # Get the start and end positions
        start_position = self.board.get_square_position(start_square)
        end_position = self.board.get_square_position(end_square)

        # Generate the board map
        map = self.board.generate_map([start_square, end_square])

        # Plot the board
        if plotting_axs is not None:
            # Set the path planner background
            self.board.plot_background(plotting_axs)

            # Plot the pieces
            self.board.plot_board(plotting_axs)

        # Setup a variable to hold the capture path
        capture_path = None

        # Check if move is capture
        if self.board.check_capture(best_move):
            # If the move is a capture, remove the piece from the board
            # Prepare the path planner
            map.clear_points()
            self.astar.set_graph(map)
        
            # Set the start and end points
            self.astar.set_start(end_position)
            self.astar.set_goal(self.board.get_open_capture_position())

            # Plan the path
            capture_path = self.astar.calculate_path()

            # Plot the capture path
            if plotting_axs is not None:
                self.astar.plot_path(plotting_axs, board.get_piece_diameter())

        # Plan the move path
        map.clear_points()
        self.astar.set_graph(map)

        self.astar.set_start(start_position)
        self.astar.set_goal(end_position)

        path = self.astar.calculate_path()
        
        # Make the move on the board
        self.board.make_move(best_move)
        
        # Plot the graph and the move path
        if plotting_axs is not None:
            map.plot_graph(plotting_axs, simplify=True)
            self.astar.plot_path(plotting_axs, self.board.get_piece_diameter())

        # Return the path
        return [capture_path, path]

    def trace_path(self, path):
        """
        Trace a pth generated by astar and return the gcode.
        
        """
        # Get the start node
        start_node = path[0]

        gcode = "G90\n"

        # Add the move to the start
        gcode += self.generate_linear_gcode(start_node)

        arc_start = None
        # Loop through the path
        for i in range(1, len(path)):
            # Get the current and previous nodes
            current_node = path[i]
            previous_node = path[i - 1]

            # Check if the current node lies on the same circle as the previous node
            if current_node.get_circle() is previous_node.get_circle():
                # If the current node is at the same position as the previous node, skip it
                if all(current_node.get_position() == previous_node.get_position()):
                    continue

                if arc_start is None:
                    arc_start = previous_node
            else:
                print(arc_start)
                if arc_start is not None:
                    gcode += "\n"
                    gcode += self.generate_arc_gcode(arc_start.get_circle(), arc_start, previous_node)
                    arc_start = None

                    gcode += "\n"
                    gcode += self.generate_linear_gcode(current_node)
                else:
                    # If it is not, generate the linear gcode
                    gcode += "\n"
                    gcode += self.generate_linear_gcode(current_node)

        return gcode

    @staticmethod
    def generate_arc_gcode(circle, start_node, end_node):
        """
        Generates the gcode for an arc move from the current position (start node) to the end node.

        """
        # Start and end positions
        start_position = start_node.get_position()
        end_position = end_node.get_position()

        # Get the parameters of the circle
        arc_center = circle.get_center()

        # Get the end position
        arc_start = v2v_angle(arc_center, start_position)
        arc_end = v2v_angle(arc_center, end_position)

        # Change the arc start and end to be between 0 and 2pi
        arc_start = zero_to_2pi(arc_start)
        arc_end = zero_to_2pi(arc_end)

        if abs(arc_start - arc_end) > np.pi:
            arc_start, arc_end = arc_end, arc_start

        # Determine if the arc is clockwise or anticlockwise
        if arc_end > arc_start:
            arc_direction = "G3" # CCW
        else:
            arc_direction = "G2" # C#

        # Calculate I and J
        print(start_position)
        arc_I = arc_center[0] - start_position[0]
        arc_J = arc_center[1] - start_position[1]
        

        return "{} X{} Y{} I{} J{} F99999999".format(arc_direction, end_position[0], end_position[1], arc_I, arc_J)
    
    @staticmethod
    def generate_linear_gcode(node):
        """
        Generates the gcode for a linear move to the node.

        """
        # Get the end positions
        end_position = node.get_position()

        return "G1 X{} Y{} F99999999".format(end_position[0], end_position[1])


if __name__ == "__main__":
    capture_positions = [
        np.array([375, 350]),
        np.array([375, 350]),
        np.array([375, 350]),
        np.array([375, 350]),
    ]

    board = PhysicalBoard(400, 400, 23, 2, capture_positions=capture_positions)
    board.reset()

    astar = Astar()
    astar.clear()

    stockfish = Stockfish(path="stockfish/stockfish_15.1_linux_x64_avx2/stockfish-ubuntu-20.04-x86-64-avx2")

    move_manager = MoveManager(board, astar, stockfish)

    # klipper = Klipper("10.29.122.93:7125", lambda x: print(x), lambda x: print(x))

    # klipper.connect()
    # klipper.check_klipper_connection()

    # board.make_move("e2e4")
    board.reset("rnbqkbnr/ppp1pppp/8/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R b KQkq - 1 2")

    fig, ax = plt.subplots()

    capture_path, path = move_manager.respond(ax)

    # print(move_manager.trace_path(capture_path))
    print(move_manager.trace_path(path))
    

    # klipper.send_gcode(move_manager.trace_path(capture_path))
    # klipper.send_gcode(move_manager.trace_path(path))

    # fig, axs = plt.subplots(2, 5)

    # for i in range(10):
    #     path = move_manager.respond(axs[int(np.floor(i / 5)), i % 5])

    plt.show()
