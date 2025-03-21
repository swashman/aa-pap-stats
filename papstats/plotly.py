# Third Party
import plotly.io as pio


def get_standard_config():
    """Return the standard config for Plotly mode bar buttons."""
    return {
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoscale"],
    }


def barchart_theme():
    template_name = "barchart_template"
    custom_template = pio.templates["seaborn"]
    custom_template.layout.update(
        plot_bgcolor="#a9a9a9",
        paper_bgcolor="#a9a9a9",
        font=dict(family="Arial", size=12, color="black"),
        xaxis=dict(
            gridcolor="#777777",
            zerolinecolor="Black",
            linecolor="#777777",
            tickcolor="#777777",
        ),
        yaxis=dict(
            gridcolor="#777777",
            zerolinecolor="Black",
            linecolor="#777777",
            tickcolor="#777777",
        ),
        title=dict(
            font=dict(size=24, weight="bold"),  # Title font settings
        ),
        legend=dict(
            traceorder="normal",  # Correct order of traces
            bgcolor="rgba(255,255,255,0.5)",  # Semi-transparent background
            bordercolor="black",
            borderwidth=1,
        ),
        xaxis_tickangle=-45,
        hovermode="x unified",
        autosize=True,
        height=600,
        margin=dict(t=50, l=50, r=50, b=50),
    )
    pio.templates[template_name] = custom_template
    return template_name
