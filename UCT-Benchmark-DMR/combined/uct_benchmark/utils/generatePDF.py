# -*- coding: utf-8 -*-
"""
Created on Mon Jun 23 13:12:25 2025

@author: Binyamin Stivi
"""

import json
from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from fpdf import FPDF

"""
This script/function generates a PDF report for UCTP benchmark results.
It includes orbit association results, binary observation metrics,
state results, and residual analysis for reference and candidate orbits.

Written by Binyamin Stivi.
"""


"""
with open('./data/raw_results.json', 'r') as file:
    data = json.load(file)
    assoc = data.get("association_results")
    binary = data.get("binary_results")[0]
    states = data.get("state_results")
    residual_ref = data.get("residual_ref_results")
    residual_cand = data.get("residual_cand_results")

    #print(assoc)
"""
path = "../data/report.pdf"


def generatePDF(data, output_path=path, path_flag=False):
    if path_flag:
        with open(data, "r") as file:
            data_f = json.load(file)
        data = data_f
    assoc = data.get("association_results")
    binary = data.get("binary_results")[0]
    states = data.get("state_results")
    residual_ref = data.get("residual_ref_results")
    residual_cand = data.get("residual_cand_results")
    """
    Generates a PDF report with the provided data.
    Can either grab the json file driectly or the dictionary as a function parameter.
    Parameters:
    - data: The raw results data.
    - assoc: Association results.
    - binary: Binary observation metrics.
    - states: State results.
    - residual_ref: Reference orbit residuals.
    - residual_cand: Candidate orbit residuals.
    """

    class MyPDF(FPDF):
        def header(self):
            self.set_fill_color(0, 6, 65)
            self.rect(x=0, y=0, w=210, h=25, style="F")
            self.set_fill_color(195, 41, 44)
            self.rect(x=0, y=24, w=210, h=5, style="F")

            self.set_font("Times", "B", 18)
            self.set_text_color(255, 255, 255)
            self.ln(2)  # Add 2 units vertical space before/after cell
            self.cell(0, 8, "UCTP Benchmark Results", ln=True, align="C")
            self.set_font("Times", "B", 16)
            self.cell(0, 10, "INSERT DATASET CODE HERE", ln=True, align="C")

            self.image("libraries/Reverse_IH-Horizontal_VT-ARC.png", x=5, y=5, w=50)
            self.image("libraries/SSC logo.png", x=170, y=3, w=12)
            self.image("libraries/TAB_LAB_invert_1.png", x=185, y=3, w=20)
            self.image("libraries/sean_explains.png", x=10, y=20, w=20)
            self.image("libraries/TicTac.png", x=195, y=285, w=5)

            self.ln(15)  # Add space below header
            self.set_text_color(0, 0, 0)  # Reset to black
            # TODO: ADD SUBTITLE THAT DEFINES EXACT TYPE OF DATA IN REPORT

    # Then use it like this:
    pdf = MyPDF()

    # os.chdir(os.path.dirname(os.path.abspath(__file__)))

    MAX_Y = 270
    custom_color_red = (195 / 255, 41 / 255, 44 / 255)

    title = "UCTP Benchmark Results"

    # pdf = FPDF()
    pdf.set_title(title)
    pdf.set_author("Binyamin Stivi")
    pdf.set_margins(left=25.4, top=0, right=25.4)
    pdf.add_page()

    ##### ORBIT ASSOCIATION

    # Set column width
    col_width = pdf.w / 4  # Adjust as needed
    row_height = 10

    # Table headers
    pdf.set_font("Times", style="B", size=12)
    pdf.cell(col_width, row_height, "Associated Orbits", border=1, align="C")
    y1 = pdf.get_y()

    pdf.cell(col_width / 1.5, row_height, "Number of Orbits", border=1, align="C")
    pdf.ln(row_height)

    # Reset font
    pdf.set_font("Times", size=10)

    # Add data rows
    for key, value in assoc.items():
        pdf.cell(col_width, row_height, str(key), border=1, align="C")
        pdf.cell(col_width / 1.5, row_height, str(value), border=1, align="C")
        pdf.ln(row_height)

    x1 = pdf.get_x()

    ##### BINARY OBSERVATION METRICS

    x2 = x1 + 90
    y2 = y1
    # Set column width
    col_width = pdf.w / 10  # Adjust as needed
    x_labels = ["Positive", "Negative"]

    # Table headers
    pdf.set_font("Times", style="B", size=12)
    pdf.set_xy(x2, y2)
    pdf.cell(col_width, row_height, "", border=1)
    for label in x_labels:
        pdf.cell(col_width, row_height, label, border=1, align="C")
    pdf.ln(row_height)
    pdf.set_x(x2)
    pdf.cell(col_width, row_height, "True", border=1, align="C")
    pdf.cell(col_width, row_height, str(binary["TruePositives"]), border=1, align="C")
    pdf.cell(col_width, row_height, str(binary["TrueNegatives"]), border=1, align="C")
    pdf.ln(row_height)
    pdf.set_x(x2)
    pdf.cell(col_width, row_height, "False", border=1, align="C")
    pdf.cell(col_width, row_height, str(binary["FalsePositives"]), border=1, align="C")
    pdf.cell(col_width, row_height, str(binary["FalseNegatives"]), border=1, align="C")

    ##### State RESULTS
    pdf.set_font("Times", style="B", size=6)
    pdf.set_xy(15, 90)

    total_table_height = 100  # mm
    num_rows = len(states)
    row_height = total_table_height / num_rows

    row_height = 5

    State_label = [
        "NORAD ID",
        "MD P-Score",
        "Pos. Error Norm",
        "Vel. Error Norm",
        "Total Bias",
        "NEES P-Score",
    ]
    pdf.set_x(pdf.l_margin)
    pdf.cell(col_width / 2, row_height, "Orbit", border=1, align="C")
    for label in State_label:
        pdf.cell(col_width, row_height, label, border=1, align="C")
    pdf.ln(row_height)
    number = len(states)
    for x in range(number):
        if pdf.get_y() > MAX_Y:
            pdf.add_page()

        pdf.cell(col_width / 2, row_height, str(x + 1), border=1, align="C")
        states_current = states[x]
        pdf.cell(col_width, row_height, str(states_current["satNo"]), border=1, align="C")
        pdf.cell(col_width, row_height, str(states_current["MD P-Score"]), border=1, align="C")
        pdf.cell(
            col_width, row_height, str(states_current["Position Error Norm"]), border=1, align="C"
        )
        pdf.cell(
            col_width, row_height, str(states_current["Velocity Error Norm"]), border=1, align="C"
        )
        pdf.cell(col_width, row_height, str(states_current["Total Bias"]), border=1, align="C")
        # pdf.cell(col_width, row_height, str(states_current["NEES"]), border=1, align="C")
        pdf.cell(col_width, row_height, str(states_current["NEES P-Score"]), border=1, align="C")

        pdf.ln(row_height)

    pdf.add_page()  ############ NEW PAGE

    ########## RESIDUAL REFERENCE
    # Step 1: Create and save the graph with matplotlib
    earliest = datetime(2099, 6, 23, 15, 30)
    latest = datetime(1970, 1, 1, 00, 00, 00)
    fig, ax = plt.subplots()
    for j in range(len(residual_ref)):
        residual_current = residual_ref[j]
        x = residual_current["Epoch"]
        y = residual_current["Residuals"]
        x_cov = []
        for i in range(len(x)):
            x_cov.append(datetime.fromisoformat(x[i]))
        earliest = min(earliest, min(x_cov))
        latest = max(latest, max(x_cov))
        ax.plot(x_cov, y, marker="o", label=str(j + 1))

    step = timedelta(hours=3)
    x_grid = []
    current = earliest
    while current <= latest:
        x_grid.append(current)
        current += step

    ax.set_xticks(x_grid)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))

    plt.gcf().autofmt_xdate()  # Auto-rotate date labels
    plt.xlabel("epoch")
    plt.ylabel("rad")
    plt.grid(True)
    plt.title("Reference Orbit Residuals")
    plt.legend()
    plt.legend(loc="upper left")  # Choose position
    plt.legend(fontsize=10)  # Set font size

    graph_filename = "graph_ref.png"
    plt.savefig(graph_filename)
    plt.close()

    # Step 2: Insert the image into a PDF with FPDF
    pdf.set_font("Arial", size=12)

    # Insert the graph image (you can adjust x, y, w, h for position and size)
    pdf.image(graph_filename, x=10, y=40, w=100)

    pdf.set_font("Times", style="B", size=6)

    ######### Residual Bar Graph

    mean = []
    std = []
    for i in range(len(residual_ref)):
        mean.append(residual_ref[i]["Mean"])
        std.append(residual_ref[i]["std"])

    plt.bar(range(number), mean, yerr=std, capsize=5, color=custom_color_red, edgecolor="black")

    # Add labels
    plt.ylabel("Rad")
    plt.xlabel("Orbit Number")
    plt.title("Mean Reference Residuals with Standard Deviation")

    plt.grid(True, axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()

    graph_filename = "graph_mean_Ref.png"
    plt.savefig(graph_filename)
    plt.close()

    # Step 2: Insert the image into a PDF with FPDF
    pdf.set_font("Arial", size=12)

    # Insert the graph image (you can adjust x, y, w, h for position and size)
    pdf.image(graph_filename, x=10, y=120, w=90)

    pdf.set_xy(10, 200)

    #### RESIDUAL REFERENCE TABLE
    pdf.set_font("Times", style="B", size=6)

    total_table_height = 100  # mm
    num_rows = len(residual_ref)
    row_height = total_table_height / num_rows
    row_height = 5
    residual_ref_label = ["RMSE", "Mean", "std deviaiton"]
    pdf.set_x(pdf.l_margin)
    pdf.cell(col_width / 2, row_height, "Orbit", border=1, align="C")
    for label in residual_ref_label:
        pdf.cell(col_width, row_height, label, border=1, align="C")
    pdf.ln(row_height)
    number = len(residual_ref)
    for x in range(number):
        if pdf.get_y() > MAX_Y:
            pdf.add_page()
        pdf.cell(col_width / 2, row_height, str(x + 1), border=1, align="C")
        residual_ref_current = residual_ref[x]
        pdf.cell(col_width, row_height, str(residual_ref_current["RMSE"]), border=1, align="C")
        pdf.cell(col_width, row_height, str(residual_ref_current["Mean"]), border=1, align="C")
        pdf.cell(col_width, row_height, str(residual_ref_current["std"]), border=1, align="C")
        pdf.ln(row_height)

    ##################### RESIDUAL CANIDATE
    # Step 1: Create and save the graph with matplotlib
    earliest = datetime(2099, 6, 23, 15, 30)
    latest = datetime(1970, 1, 1, 00, 00, 00)
    fig, ax_cand = plt.subplots()
    for j in range(len(residual_cand)):
        residual_current = residual_cand[j]
        x = residual_current["Epoch"]
        y = residual_current["Residuals"]
        x_cov = []
        for i in range(len(x)):
            x_cov.append(datetime.fromisoformat(x[i]))
        earliest = min(earliest, min(x_cov))
        latest = max(latest, max(x_cov))
        ax_cand.plot(x_cov, y, marker="o", label=str(j + 1))

    step = timedelta(hours=3)
    x_grid = []
    current = earliest
    while current <= latest:
        x_grid.append(current)
        current += step

    ax_cand.set_xticks(x_grid)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))

    plt.gcf().autofmt_xdate()  # Auto-rotate date labels
    plt.xlabel("epoch")
    plt.ylabel("rad")
    plt.grid(True)
    plt.title("Canidate Orbit Residuals")
    plt.legend()
    plt.legend(loc="upper left")  # Choose position
    plt.legend(fontsize=10)  # Set font size

    graph_filename = "graph_cand.png"
    plt.savefig(graph_filename)
    plt.close()

    # Step 2: Insert the image into a PDF with FPDF
    pdf.set_font("Arial", size=12)

    # Insert the graph image (you can adjust x, y, w, h for position and size)
    pdf.image(graph_filename, x=100, y=40, w=100)

    ######### Residual Bar Graph

    mean = []
    std = []
    for i in range(len(residual_cand)):
        mean.append(residual_cand[i]["Mean"])
        std.append(residual_cand[i]["std"])

    plt.bar(range(number), mean, yerr=std, capsize=5, color=custom_color_red, edgecolor="black")

    # Add labels
    plt.ylabel("Rad")
    plt.xlabel("Orbit Number")
    plt.title("Mean Canidate Residuals with Standard Deviation")

    plt.grid(True, axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()

    graph_filename = "graph_mean_cand.png"
    plt.savefig(graph_filename)
    plt.close()

    # Step 2: Insert the image into a PDF with FPDF
    pdf.set_font("Arial", size=12)

    # Insert the graph image (you can adjust x, y, w, h for position and size)
    pdf.image(graph_filename, x=100, y=120, w=90)

    ####### RESIDUAL CANDIDATE TABLE
    pdf.set_font("Times", style="B", size=6)

    total_table_height = 100
    num_rows = len(residual_cand)
    row_height = total_table_height / num_rows
    row_height = 5
    residual_cand_label = ["RMSE", "Mean", "std deviation"]

    pdf.set_xy(110, 200)
    pdf.cell(col_width / 2, row_height, "Orbit", border=1, align="C")
    for label in residual_cand_label:
        pdf.cell(col_width, row_height, label, border=1, align="C")
    pdf.ln(row_height)
    number = len(residual_cand)
    for x in range(number):
        if pdf.get_y() > MAX_Y:
            pdf.add_page()
        pdf.set_x(110)
        pdf.cell(col_width / 2, row_height, str(x + 1), border=1, align="C")
        residual_cand_current = residual_cand[x]
        pdf.cell(col_width, row_height, str(residual_cand_current["RMSE"]), border=1, align="C")
        pdf.cell(col_width, row_height, str(residual_cand_current["Mean"]), border=1, align="C")
        pdf.cell(col_width, row_height, str(residual_cand_current["std"]), border=1, align="C")
        pdf.ln(row_height)

    pdf.output(path, "F")
