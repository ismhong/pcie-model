#!/usr/bin/env python3
"""
Gradio UI for PCIe Bandwidth Visualization Tool
"""

import os
import tempfile
import subprocess
import gradio as gr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from model import pcie, eth, mem_bw, simple_nic, niantic

def run_pcie_model(pcie_version, lanes, addr_width, ecrc, mps, mrrs, rcb, ethernet_speed):
    """Run the PCIe model with the specified parameters and generate graphs"""
    # Convert parameters to appropriate types
    addr_width = int(addr_width)
    ecrc = int(ecrc)
    mps = int(mps)
    mrrs = int(mrrs)
    rcb = int(rcb)
    
    # Create PCIe configuration
    pciecfg = pcie.Cfg(
        version=pcie_version,
        lanes=lanes,
        addr=addr_width,
        ecrc=ecrc,
        mps=mps,
        mrrs=mrrs,
        rcb=rcb
    )
    
    # Print PCIe configuration
    config_info = []
    config_info.append(f"PCIe Config:")
    config_info.append(f"  Version:    {pciecfg.version}")
    config_info.append(f"  Lanes:      {pciecfg.lanes}")
    config_info.append(f"  Addr bits:  {pciecfg.addr}")
    config_info.append(f"  ECRC:       {pciecfg.ecrc}")
    config_info.append(f"  MPS:        {pciecfg.mps}")
    config_info.append(f"  MRRS:       {pciecfg.mrrs}")
    config_info.append(f"  RCB:        {pciecfg.rcb}")
    config_info.append(f"  TLP BW:     {pciecfg.TLP_bw:.2f} Gb/s")
    config_info.append(f"  RAW BW:     {pciecfg.RAW_bw:.2f} Gb/s")
    
    # Create Ethernet configuration
    ethcfg = eth.Cfg(ethernet_speed)
    
    # Set up bandwidth specifications
    tlp_bw = pciecfg.TLP_bw
    bw_spec = pcie.BW_Spec(tlp_bw, tlp_bw, pcie.BW_Spec.BW_RAW)
    
    # Create temporary data file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as tmp_file:
        data_file = tmp_file.name
    
    # Generate data
    sizes = []
    wr_bw_values = []
    rd_bw_values = []
    rdwr_bw_values = []
    eth_bw_values = []
    simple_nic_bi_values = []
    kernel_nic_bi_values = []
    pmd_nic_bi_values = []
    
    for size in range(64, 1500 + 1):
        # Calculate PCIe bandwidths
        wr_bw = mem_bw.write(pciecfg, bw_spec, size - 4)
        rd_bw = mem_bw.read(pciecfg, bw_spec, size - 4)
        rdwr_bw = mem_bw.read_write(pciecfg, bw_spec, size - 4)
        
        # Calculate Ethernet bandwidth
        eth_bw = ethcfg.bps_ex(size - 4) / (1000 * 1000 * 1000.0)
        
        # Calculate NIC bandwidths
        simple_nic_bi = simple_nic.bw(pciecfg, bw_spec, pcie.DIR_BOTH, size - 4)
        kernel_nic_bi = niantic.bw(pciecfg, bw_spec, pcie.DIR_BOTH, size - 4)
        pmd_nic_bi = niantic.bw(pciecfg, bw_spec, pcie.DIR_BOTH, size - 4, h_opt="PMD")
        
        # Store values
        sizes.append(size)
        wr_bw_values.append(wr_bw.tx_eff)
        rd_bw_values.append(rd_bw.rx_eff)
        rdwr_bw_values.append(rdwr_bw.tx_eff)
        eth_bw_values.append(eth_bw)
        simple_nic_bi_values.append(simple_nic_bi.tx_eff)
        kernel_nic_bi_values.append(kernel_nic_bi.tx_eff)
        pmd_nic_bi_values.append(pmd_nic_bi.tx_eff)
    
    # Create dataframe for table display
    df = pd.DataFrame({
        'Transfer Size (Bytes)': sizes,
        'PCIe Write BW (Gb/s)': wr_bw_values,
        'PCIe Read BW (Gb/s)': rd_bw_values,
        'PCIe Read/Write BW (Gb/s)': rdwr_bw_values,
        '40G Ethernet (Gb/s)': eth_bw_values,
        'Simple NIC (Gb/s)': simple_nic_bi_values,
        'Modern NIC (kernel driver) (Gb/s)': kernel_nic_bi_values,
        'Modern NIC (DPDK driver) (Gb/s)': pmd_nic_bi_values
    })
    
    # Sample the dataframe to show fewer rows
    sampled_df = df.iloc[::50].reset_index(drop=True)
    
    # Create interactive plot with plotly
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=sizes, 
        y=rdwr_bw_values, 
        mode='lines', 
        name='Effective PCIe BW',
        line=dict(color='black', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=sizes, 
        y=eth_bw_values, 
        mode='lines', 
        name=f'{ethernet_speed}',
        line=dict(color='blue', width=2, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=sizes, 
        y=simple_nic_bi_values, 
        mode='lines', 
        name='Simple NIC',
        line=dict(color='green', width=2, dash='dot')
    ))
    
    fig.add_trace(go.Scatter(
        x=sizes, 
        y=kernel_nic_bi_values, 
        mode='lines', 
        name='Modern NIC (kernel driver)',
        line=dict(color='gray', width=2, dash='dashdot')
    ))
    
    fig.add_trace(go.Scatter(
        x=sizes, 
        y=pmd_nic_bi_values, 
        mode='lines', 
        name='Modern NIC (DPDK driver)',
        line=dict(color='red', width=2)
    ))
    
    fig.update_layout(
        title='PCIe and Ethernet Bandwidth Comparison',
        xaxis_title='Transfer Size (Bytes)',
        yaxis_title='Bandwidth (Gb/s)',
        hovermode='closest',
        legend=dict(x=0.02, y=0.98),
        width=900,
        height=500,
        template='plotly_white'
    )
    
    # Add hover information
    fig.update_traces(
        hoverinfo='all',
        hovertemplate='Size: %{x} bytes<br>Bandwidth: %{y:.2f} Gb/s<extra></extra>'
    )
    
    # Save plot to temporary file
    plot_html = fig.to_html(include_plotlyjs='cdn', full_html=False)
    
    return "\n".join(config_info), plot_html, sampled_df

# Create Gradio interface
with gr.Blocks(title="PCIe Bandwidth Visualization Tool") as demo:
    gr.Markdown("# PCIe Bandwidth Visualization Tool")
    gr.Markdown("Select parameters to calculate and visualize PCIe bandwidth")
    
    with gr.Row():
        with gr.Column(scale=1):
            pcie_version = gr.Dropdown(
                choices=["gen1", "gen2", "gen3", "gen4", "gen5"],
                value="gen3",
                label="PCIe Version"
            )
            lanes = gr.Dropdown(
                choices=["x1", "x2", "x4", "x8", "x16", "x32"],
                value="x8",
                label="Number of Lanes"
            )
            addr_width = gr.Dropdown(
                choices=["32", "64"],
                value="64",
                label="Address Width (bits)"
            )
            ecrc = gr.Dropdown(
                choices=["0", "1"],
                value="0",
                label="ECRC"
            )
        
        with gr.Column(scale=1):
            mps = gr.Dropdown(
                choices=["128", "256", "512", "1024", "2048", "4096"],
                value="256",
                label="Maximum Payload Size (MPS)"
            )
            mrrs = gr.Dropdown(
                choices=["128", "256", "512", "1024", "2048", "4096"],
                value="512",
                label="Maximum Read Request Size (MRRS)"
            )
            rcb = gr.Dropdown(
                choices=["64", "128"],
                value="64",
                label="Read Completion Boundary (RCB)"
            )
            ethernet_speed = gr.Dropdown(
                choices=["10GigE", "25GigE", "40GigE", "50GigE", "100GigE", "200GigE", "400GigE"],
                value="40GigE",
                label="Ethernet Speed"
            )
            run_button = gr.Button("Calculate and Visualize", variant="primary")
    
    with gr.Row():
        with gr.Column(scale=1):
            config_output = gr.Textbox(label="PCIe Configuration", lines=12)
        with gr.Column(scale=2):
            plot_output = gr.HTML(label="Bandwidth Comparison Plot")
    
    with gr.Row():
        table_output = gr.DataFrame(label="Bandwidth Data (Sampled)")
    
    run_button.click(
        fn=run_pcie_model,
        inputs=[pcie_version, lanes, addr_width, ecrc, mps, mrrs, rcb, ethernet_speed],
        outputs=[config_output, plot_output, table_output]
    )

if __name__ == "__main__":
    demo.launch()
