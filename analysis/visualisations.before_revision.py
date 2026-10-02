"""
visualisations.py
Phase 5 — Results Visualisation
Robustness Testing for LLM-Based Text-to-Cypher Systems

Generates all charts and figures for the final report.
All figures saved as high-resolution PNG files in outputs/.

Figures produced:
1. Error type distribution bar chart
2. BLEU score distribution by error type (box plot)
3. Error rate by complexity level (grouped bar chart)
4. BLEU score by complexity level (box plot)
5. Spearman correlation heatmap
6. Exact Match vs BLEU scatter plot

"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import os

# ─────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────

plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
COLOURS = ['#2196F3', '#FF5722', '#4CAF50', '#FF9800']
OUTPUT_DIR = "outputs"


def load_data():
    df = pd.read_csv("data/generated_queries.csv")
    df['bleu_score'] = df['bleu_score'].fillna(0).astype(float)
    df['exact_match'] = df['exact_match'].fillna(0).astype(int)
    df['syntax_error'] = df['syntax_error'].fillna(0).astype(int)
    df['schema_hallucination'] = df['schema_hallucination'].fillna(0).astype(int)
    df['logical_error'] = df['logical_error'].fillna(0).astype(int)
    df['performance_error'] = df['performance_error'].fillna(0).astype(int)
    df['complexity'] = df['complexity'].fillna('unknown')
    df['any_error'] = (
        (df['syntax_error'] == 1) |
        (df['schema_hallucination'] == 1) |
        (df['logical_error'] == 1) |
        (df['performance_error'] == 1)
    ).astype(int)
    return df


# ─────────────────────────────────────────
# FIGURE 1 — Error type distribution
# ─────────────────────────────────────────

def fig1_error_distribution(df):
    error_labels = [
        'Syntax\nError',
        'Schema\nHallucination',
        'Logical\nError',
        'Performance\nIssue'
    ]
    counts = [
        df['syntax_error'].sum(),
        df['schema_hallucination'].sum(),
        df['logical_error'].sum(),
        df['performance_error'].sum()
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(error_labels, counts, color=COLOURS, edgecolor='white', width=0.5)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 0.3,
                f'{count}\n({count/200*100:.1f}%)',
                ha='center', va='bottom', fontsize=10)

    ax.set_title('Error Type Distribution Across 200 Generated Cypher Queries',
                 fontweight='bold', pad=15)
    ax.set_ylabel('Number of Queries')
    ax.set_xlabel('Error Type')
    ax.set_ylim(0, max(counts) * 1.25)
    ax.axhline(y=0, color='black', linewidth=0.5)
    sns.despine()

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/fig1_error_distribution.png"
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Saved → {path}")


# ─────────────────────────────────────────
# FIGURE 2 — BLEU by error type (box plot)
# ─────────────────────────────────────────

def fig2_bleu_by_error(df):
    groups = {
        'No Error': df[df['any_error'] == 0]['bleu_score'],
        'Schema\nHallucination': df[df['schema_hallucination'] == 1]['bleu_score'],
        'Logical\nError': df[df['logical_error'] == 1]['bleu_score'],
        'Performance\nIssue': df[df['performance_error'] == 1]['bleu_score']
    }

    fig, ax = plt.subplots(figsize=(10, 5))
    bp = ax.boxplot(groups.values(), patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2))

    colours = ['#4CAF50', '#FF5722', '#2196F3', '#FF9800']
    for patch, colour in zip(bp['boxes'], colours):
        patch.set_facecolor(colour)
        patch.set_alpha(0.7)

    ax.set_xticklabels(groups.keys())
    ax.set_title('BLEU Score Distribution by Error Type',
                 fontweight='bold', pad=15)
    ax.set_ylabel('BLEU Score')
    ax.set_xlabel('Error Type')
    ax.set_ylim(-5, 110)
    sns.despine()

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/fig2_bleu_by_error.png"
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Saved → {path}")


# ─────────────────────────────────────────
# FIGURE 3 — Error rate by complexity
# ─────────────────────────────────────────

def fig3_error_by_complexity(df):
    complexity_order = ['simple', 'medium', 'complex']
    error_cols = {
        'Schema Hallucination': 'schema_hallucination',
        'Logical Error': 'logical_error',
        'Performance Issue': 'performance_error'
    }

    n_per_complexity = df.groupby('complexity').size()
    x = np.arange(len(complexity_order))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))

    for idx, (label, col) in enumerate(error_cols.items()):
        rates = [
            df[df['complexity'] == c][col].sum() /
            n_per_complexity[c] * 100
            for c in complexity_order
        ]
        offset = (idx - 1) * width
        bars = ax.bar(x + offset, rates, width,
                      label=label, color=COLOURS[idx+1],
                      edgecolor='white', alpha=0.85)
        for bar, rate in zip(bars, rates):
            if rate > 0:
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.3,
                        f'{rate:.0f}%',
                        ha='center', va='bottom', fontsize=9)

    ax.set_title('Error Rate by Query Complexity Level',
                 fontweight='bold', pad=15)
    ax.set_ylabel('Error Rate (%)')
    ax.set_xlabel('Complexity Level')
    ax.set_xticks(x)
    ax.set_xticklabels([c.capitalize() for c in complexity_order])
    ax.set_ylim(0, 35)
    ax.legend(loc='upper right')
    sns.despine()

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/fig3_error_by_complexity.png"
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Saved → {path}")


# ─────────────────────────────────────────
# FIGURE 4 — BLEU by complexity (box plot)
# ─────────────────────────────────────────

def fig4_bleu_by_complexity(df):
    complexity_order = ['simple', 'medium', 'complex']
    groups = [df[df['complexity'] == c]['bleu_score']
              for c in complexity_order]

    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(groups, patch_artist=True,
                    medianprops=dict(color='black', linewidth=2))

    colours = ['#64B5F6', '#42A5F5', '#1565C0']
    for patch, colour in zip(bp['boxes'], colours):
        patch.set_facecolor(colour)
        patch.set_alpha(0.7)

    means = [g.mean() for g in groups]
    ax.plot([1, 2, 3], means, 'D--', color='red',
            markersize=6, label='Mean', linewidth=1.5)

    ax.set_xticklabels([c.capitalize() for c in complexity_order])
    ax.set_title('BLEU Score Distribution by Query Complexity Level',
                 fontweight='bold', pad=15)
    ax.set_ylabel('BLEU Score')
    ax.set_xlabel('Complexity Level')
    ax.set_ylim(-5, 110)
    ax.legend()
    sns.despine()

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/fig4_bleu_by_complexity.png"
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Saved → {path}")


# ─────────────────────────────────────────
# FIGURE 5 — BLEU vs Exact Match scatter
# ─────────────────────────────────────────

def fig5_bleu_vs_em(df):
    fig, ax = plt.subplots(figsize=(8, 5))

    colours = df['any_error'].map({0: '#4CAF50', 1: '#F44336'})
    ax.scatter(df['bleu_score'], df['exact_match'],
               c=colours, alpha=0.5, edgecolors='none', s=40)

    # Highlight BLEU=100 EM=0 cases
    special = df[(df['bleu_score'] == 100) & (df['exact_match'] == 0)]
    ax.scatter(special['bleu_score'], special['exact_match'],
               c='orange', s=80, zorder=5,
               label=f'BLEU=100, EM=0 (n={len(special)})',
               edgecolors='darkorange')

    error_patch = mpatches.Patch(color='#F44336', alpha=0.6, label='Has Error')
    clean_patch = mpatches.Patch(color='#4CAF50', alpha=0.6, label='No Error')
    ax.legend(handles=[clean_patch, error_patch,
                        ax.get_legend_handles_labels()[0][-1]])

    ax.set_title('BLEU Score vs Exact Match by Error Status',
                 fontweight='bold', pad=15)
    ax.set_xlabel('BLEU Score')
    ax.set_ylabel('Exact Match (0 or 1)')
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['No Match (0)', 'Exact Match (1)'])
    sns.despine()

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/fig5_bleu_vs_em.png"
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"Saved → {path}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def run_visualisations():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data()

    print("Generating Visualisations")
    print("="*50)

    fig1_error_distribution(df)
    fig2_bleu_by_error(df)
    fig3_error_by_complexity(df)
    fig4_bleu_by_complexity(df)
    fig5_bleu_vs_em(df)

    print("="*50)
    print("All figures saved to outputs/")


if __name__ == "__main__":
    run_visualisations()