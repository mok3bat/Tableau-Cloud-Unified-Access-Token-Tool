import gradio as gr
import os
from datetime import datetime, timedelta
import uuid
import jwt as pyjwt


# Import our authentication modules
from auth.keygen import generate_key_pair
from auth.cloud_manager_auth import login_cloud_manager_pat, login_tcm_with_jwt
from auth.uat_config import create_uat_config
from auth.tableau_auth import login_tableau_cloud

# Import managers modules
from managers.site_manager import SiteManager
from managers.resource_managers import ResourceManager
from managers.scope_manager import ScopeManager

# Create instances
site_manager = SiteManager()
tenant_manager = ResourceManager('tenant')
project_manager = ResourceManager('project')
workbook_manager = ResourceManager('workbook')
datasource_manager = ResourceManager('datasource')
flow_manager = ResourceManager('flow')
scope_manager = ScopeManager()

def create_uat_config_tool():
    
    with gr.Blocks(title="Tableau UAT Configuration Tool", analytics_enabled=False) as app:
        gr.Markdown("# Tableau UAT Configuration Tool")
        gr.Markdown("This tool guides you through the UAT configuration process.")
        
        with gr.Tabs():
            with gr.TabItem("Configuration"):

                gr.Markdown("""
                <div style='padding: 15px; background: #e7f3ff; border-left: 4px solid #0d6efd; border-radius: 4px; margin-bottom: 20px;'>
                    <strong>ℹ️ Quick Start Guide:</strong><br>
                    <ol style='margin: 10px 0; padding-left: 20px;'>
                        <li>Fill in <strong>Cloud Manager Settings</strong> (Tenant ID, PAT Secret)</li>
                        <li>Fill in <strong>Tableau Cloud Settings</strong> (Pod URL, Username)</li>
                        <li><strong>Required:</strong> Add at least one <strong>Resource</strong> Tenant, Site, Projects, Workbooks, etc.</li>
                        <li>Click <strong>"Start UAT Configuration Workflow"</strong></li>
                    </ol>
                    <small style='color: #495057;'><strong>Note:</strong> Site LUID must be a valid 36-character UUID (e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890)</small>
                </div>
                """)

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Cloud Manager Settings")
                        cm_tenant_id = gr.Textbox(label="Tenant ID", placeholder="xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx")
                        cm_pat_secret = gr.Textbox(label="PAT Secret", type="password")
                        cm_pat_login_url = gr.Textbox(label="PAT Login URL", value="https://cloudmanager.tableau.com/api/v1/pat/login")
                        cm_jwt_login_url = gr.Textbox(label="JWT Login URL", value="https://cloudmanager.tableau.com/api/v1/jwt/login", placeholder="https://{tenant}.cloudmanager.tableau.com/api/v1/jwt/login")
                        cm_uat_configs_url = gr.Textbox(label="UAT Configs URL", value="https://cloudmanager.tableau.com/api/v1/uat-configurations", placeholder="https://{tenant}.cloudmanager.tableau.com/api/v1/uat-configurations")
                        uat_config_name = gr.Textbox(label="UAT Config Name", value="My-UAT-Config", placeholder="A unique name for your configuration")
                    
                    with gr.Column():
                        gr.Markdown("### Tableau Cloud Settings")
                        tc_pod_url = gr.Textbox(label="Pod URL", placeholder="https://10ax.online.tableau.com")
                        tc_username = gr.Textbox(label="Username", placeholder="user@example.com")
                        
                        gr.Markdown("#### 🌐 Sites Configuration")
                        gr.Markdown(
                            "<small style='color: #6c757d;'>Add one or more sites you want to access with this token</small>"
                        )
                        
                        with gr.Row():
                            site_id_input = gr.Textbox(
                                label="Site ID (contentUrl)",
                                placeholder="sandboxdev",
                                scale=2
                            )
                            site_luid_input = gr.Textbox(
                                label="Site LUID",
                                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxx",
                                scale=2
                            )
                            site_scope_input = gr.Dropdown(
                                label="Scope",
                                choices=["tableau:content:read", "tableau:content:write", "tableau:content:*"],
                                value="tableau:content:read",
                                scale=1
                            )
                        
                        with gr.Row():
                            add_site_btn = gr.Button("➕ Add Site", variant="primary", size="sm")
                            clear_sites_btn = gr.Button("🗑️ Clear All Sites", variant="secondary", size="sm")
                        
                        # Display sites
                        gr.Markdown("##### 📋 Configured Sites")
                        sites_display = gr.HTML(
                            value="<div style='padding: 15px; background: #f8f9fa; border-radius: 8px; border: 2px dashed #dee2e6; text-align: center; color: #6c757d; font-style: italic;'>No sites configured yet</div>"
                        )
                        
                        # Site selector for deletion
                        site_selector = gr.Radio(
                            choices=[],
                            label="Select site to delete",
                            visible=False,
                            show_label=False
                        )
                        delete_site_btn = gr.Button("🗑️ Delete Selected Site", variant="stop", size="sm", visible=False)
                    
                    with gr.Column():
                        gr.Markdown("### JWT Configuration")
                        jwt_issuer = gr.Textbox(label="Issuer", visible=True)
                        
                        gr.Markdown("#### ⏱️ Token Expiration")
                        jwt_expiration = gr.Slider(
                            minimum=1,
                            maximum=60,
                            value=5,
                            step=1,
                            label="JWT Token Lifetime (minutes)",
                            info="How long the JWT token will be valid"
                        )
                        
                        gr.Markdown("#### 🎯 Resource Access Control")
                        gr.Markdown(
                            "<small style='color: #6c757d;'>Configure which resources the token can access. Resource IDs (LUIDs) will be added to UAT config, and corresponding scopes will be added to JWT.</small>"
                        )
                        
                        # Tenant Access
                        with gr.Group():
                            gr.Markdown("##### 🏢 Tenant Access (Cloud Manager)")
                            enable_tenant = gr.Checkbox(
                                label="Enable Tenant Access",
                                value=False,
                                info="Grants access to Cloud Manager tenant operations (Tenant LUID will be auto-populated from Cloud Manager settings)"
                            )
                            with gr.Row():
                                tenant_luid_display = gr.Textbox(
                                    label="Tenant LUID",
                                    placeholder="Will be auto-populated from Tenant ID above",
                                    interactive=False,
                                    scale=2,
                                    visible=False
                                )
                                tenant_scope = gr.Dropdown(
                                    label="Scope",
                                    choices=["tableau:tcm:read", "tableau:tcm:write", "tableau:tcm:*"],
                                    value="tableau:tcm:read",
                                    scale=1,
                                    visible=False
                                )
                            
                            with gr.Row():
                                add_tenant_btn = gr.Button("➕ Add Tenant Scope", variant="primary", size="sm", visible=False)
                                clear_tenants_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm", visible=False)
                            
                            tenants_display = gr.HTML(value="<div style='padding: 15px; background: #f8f9fa; border-radius: 8px; border: 2px dashed #dee2e6; text-align: center; color: #6c757d; font-style: italic;'>No tenant scopes configured yet</div>", visible=False)
                            tenant_selector = gr.Radio(choices=[], label="Select to delete", visible=False, show_label=False)
                            delete_tenant_btn = gr.Button("🗑️ Delete Selected", variant="stop", size="sm", visible=False)
                        
                        # Project Access
                        with gr.Group():
                            gr.Markdown("##### 📁 Project Access (Tableau Cloud)")
                            enable_projects = gr.Checkbox(
                                label="Enable Project Access",
                                value=False,
                                info="Grants access to specific projects"
                            )
                            with gr.Row():
                                project_luid = gr.Textbox(
                                    label="Project LUID",
                                    placeholder="Enter project LUID",
                                    scale=2,
                                    visible=False
                                )
                                project_scope = gr.Dropdown(
                                    label="Scope",
                                    choices=["tableau:projects:read", "tableau:projects:write", "tableau:projects:*"],
                                    value="tableau:projects:read",
                                    scale=1,
                                    visible=False
                                )
                            
                            with gr.Row():
                                add_project_btn = gr.Button("➕ Add Project", variant="primary", size="sm", visible=False)
                                clear_projects_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm", visible=False)
                            
                            projects_display = gr.HTML(project_manager.get_display(), visible=False)
                            project_selector = gr.Radio(choices=[], label="Select to delete", visible=False, show_label=False)
                            delete_project_btn = gr.Button("🗑️ Delete Selected", variant="stop", size="sm", visible=False)
                        
                        # Workbook Access
                        with gr.Group():
                            gr.Markdown("##### 📊 Workbook Access (Tableau Cloud)")
                            enable_workbooks = gr.Checkbox(
                                label="Enable Workbook Access",
                                value=False,
                                info="Grants access to specific workbooks"
                            )
                            with gr.Row():
                                workbook_luid = gr.Textbox(
                                    label="Workbook LUID",
                                    placeholder="Enter workbook LUID",
                                    scale=2,
                                    visible=False
                                )
                                workbook_scope = gr.Dropdown(
                                    label="Scope",
                                    choices=["tableau:workbooks:read", "tableau:workbooks:write", "tableau:workbooks:*"],
                                    value="tableau:workbooks:read",
                                    scale=1,
                                    visible=False
                                )
                            
                            with gr.Row():
                                add_workbook_btn = gr.Button("➕ Add Workbook", variant="primary", size="sm", visible=False)
                                clear_workbooks_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm", visible=False)
                            
                            workbooks_display = gr.HTML(workbook_manager.get_display(), visible=False)
                            workbook_selector = gr.Radio(choices=[], label="Select to delete", visible=False, show_label=False)
                            delete_workbook_btn = gr.Button("🗑️ Delete Selected", variant="stop", size="sm", visible=False)
                        
                        # Datasource Access
                        with gr.Group():
                            gr.Markdown("##### 🗄️ Datasource Access (Tableau Cloud)")
                            enable_datasources = gr.Checkbox(
                                label="Enable Datasource Access",
                                value=False,
                                info="Grants access to specific datasources"
                            )
                            with gr.Row():
                                datasource_luid = gr.Textbox(
                                    label="Datasource LUID",
                                    placeholder="Enter datasource LUID",
                                    scale=2,
                                    visible=False
                                )
                                datasource_scope = gr.Dropdown(
                                    label="Scope",
                                    choices=["tableau:datasources:read", "tableau:datasources:write", "tableau:datasources:*"],
                                    value="tableau:datasources:read",
                                    scale=1,
                                    visible=False
                                )
                            
                            with gr.Row():
                                add_datasource_btn = gr.Button("➕ Add Datasource", variant="primary", size="sm", visible=False)
                                clear_datasources_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm", visible=False)
                            
                            datasources_display = gr.HTML(datasource_manager.get_display(), visible=False)
                            datasource_selector = gr.Radio(choices=[], label="Select to delete", visible=False, show_label=False)
                            delete_datasource_btn = gr.Button("🗑️ Delete Selected", variant="stop", size="sm", visible=False)
                        
                        # Flow Access
                        with gr.Group():
                            gr.Markdown("##### 🔄 Flow Access (Tableau Cloud)")
                            enable_flows = gr.Checkbox(
                                label="Enable Flow Access",
                                value=False,
                                info="Grants access to specific flows"
                            )
                            with gr.Row():
                                flow_luid = gr.Textbox(
                                    label="Flow LUID",
                                    placeholder="Enter flow LUID",
                                    scale=2,
                                    visible=False
                                )
                                flow_scope = gr.Dropdown(
                                    label="Scope",
                                    choices=["tableau:flows:read", "tableau:flows:write", "tableau:flows:*"],
                                    value="tableau:flows:read",
                                    scale=1,
                                    visible=False
                                )
                            
                            with gr.Row():
                                add_flow_btn = gr.Button("➕ Add Flow", variant="primary", size="sm", visible=False)
                                clear_flows_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm", visible=False)
                            
                            flows_display = gr.HTML(flow_manager.get_display(), visible=False)
                            flow_selector = gr.Radio(choices=[], label="Select to delete", visible=False, show_label=False)
                            delete_flow_btn = gr.Button("🗑️ Delete Selected", variant="stop", size="sm", visible=False)
                        
                        gr.Markdown("---")
                        gr.Markdown("#### 📋 Current Configuration Summary")
                        config_summary = gr.HTML(
                            value="<div style='padding: 15px; background: #f8f9fa; border-radius: 8px;'><em>Enable resources above to see configuration summary</em></div>"
                        )
                
                start_btn = gr.Button("▶️ Start UAT Configuration Workflow", variant="primary", size="lg")
                status_output = gr.Textbox(label="Status", interactive=False, lines=8)
                result_output = gr.JSON(label="Detailed Results", visible=True, open=True)

                with gr.Row():
                    private_key_file = gr.File(label="🔒 Private Key (KEEP SECRET)", visible=False)
                    public_key_file = gr.File(label="🔓 Public Key (Safe to Share)", visible=False)
                
                # Hidden component to pass scopes to workflow
                selected_scopes_df = gr.DataFrame(visible=False, value=scope_manager.get_scopes_df())
                
            with gr.TabItem("Testing"):
                gr.Markdown("# 🧪 API Testing & Validation")
                gr.Markdown("Test your JWT authentication and view UAT configurations.")
                
                # JWT Authentication Tests
                gr.Markdown("## 🔐 JWT Authentication Tests")
                gr.Markdown("**Note:** Run the workflow first to generate a JWT token before testing.")
                
                with gr.Row():
                    with gr.Column():
                        with gr.Group():
                            gr.Markdown("### Tableau Cloud Manager (TCM) API")
                            gr.Markdown(
                                "<small style='color: #6c757d;'>Test JWT authentication with Cloud Manager API</small>"
                            )
                            test_tcm_btn = gr.Button("▶️ Test TCM Login", variant="primary", size="lg")
                            test_tcm_output = gr.Textbox(
                                label="Result", 
                                interactive=False, 
                                lines=3,
                                placeholder="Click 'Test TCM Login' to check authentication..."
                            )
                            with gr.Accordion("📋 cURL Command", open=False):
                                tcm_curl = gr.Code(
                                    label="", 
                                    language="shell", 
                                    interactive=False, 
                                    lines=6,
                                    value="Run the workflow first to generate the cURL command"
                                )
                    
                    with gr.Column():
                        with gr.Group():
                            gr.Markdown("### Tableau Cloud REST API")
                            gr.Markdown(
                                "<small style='color: #6c757d;'>Test JWT authentication with Tableau Cloud</small>"
                            )
                            test_tc_btn = gr.Button("▶️ Test Tableau Cloud Login", variant="primary", size="lg")
                            test_tc_output = gr.Textbox(
                                label="Result", 
                                interactive=False, 
                                lines=3,
                                placeholder="Click 'Test Tableau Cloud Login' to check authentication..."
                            )
                            with gr.Accordion("📋 cURL Command", open=False):
                                tc_curl = gr.Code(
                                    label="", 
                                    language="shell", 
                                    interactive=False, 
                                    lines=6,
                                    value="Run the workflow first to generate the cURL command"
                                )
                
                gr.Markdown("---")
                
                # UAT Configurations Section
                gr.Markdown("## 📋 UAT Configuration Management")
                gr.Markdown("View and manage UAT configurations in your Cloud Manager tenant.")
                
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=3):
                            list_configs_btn = gr.Button(
                                "🔍 List All UAT Configurations", 
                                variant="secondary", 
                                size="lg"
                            )
                        with gr.Column(scale=2):
                            gr.Markdown(
                                "<small style='color: #6c757d;'>💡 This retrieves all configurations from Cloud Manager</small>"
                            )
                    
                    configs_output = gr.JSON(
                    label="📊 Configuration Details", 
                    visible=True, 
                    open=True
                )
                
                with gr.Accordion("📋 cURL Command", open=False):
                    configs_curl = gr.Code(
                        label="", 
                        language="shell", 
                        interactive=False, 
                        lines=5,
                        value="Click 'List All UAT Configurations' to see the cURL command"
                    )
                
                # Configuration selector for revocation
                gr.Markdown("##### 🗑️ Revoke Configuration")
                gr.Markdown(
                    "<small style='color: #6c757d;'>Select a configuration ID from the list above to revoke it</small>"
                )
                config_selector = gr.Radio(
                    choices=[],
                    label="Select configuration to revoke",
                    visible=False,
                    show_label=True
                )
                
                with gr.Row():
                    revoke_config_btn = gr.Button(
                        "🗑️ Revoke Selected Configuration", 
                        variant="stop", 
                        size="lg",
                        visible=False
                    )
                
                revoke_output = gr.JSON(
                    label="Revoke Result",
                    visible=False
                )
                
                with gr.Accordion("📋 Revoke cURL Command", open=False, visible=False) as revoke_curl_accordion:
                    revoke_curl = gr.Code(
                        label="", 
                        language="shell", 
                        interactive=False, 
                        lines=4,
                        value=""
                    )

        # --- EVENT HANDLER FUNCTIONS ---
        
        def add_site_handler(site_id, site_luid, site_scope):
            """Handle adding a site"""
            sites_display, site_choices, status_msg = site_manager.add_site(site_id, site_luid, site_scope)
            selector_visible = bool(site_manager.sites)
            
            return (
                sites_display,
                gr.Radio(choices=site_choices, visible=selector_visible, show_label=False),
                gr.Button(visible=selector_visible),
                status_msg,
                generate_config_summary()
            )
        
        def delete_site_handler(selected_site):
            """Handle deleting a site"""
            sites_display, site_choices, status_msg = site_manager.delete_site(selected_site)
            selector_visible = bool(site_manager.sites)
            
            return (
                sites_display,
                gr.Radio(choices=site_choices, visible=selector_visible, show_label=False),
                gr.Button(visible=selector_visible),
                status_msg,
                generate_config_summary()
            )
        
        def clear_sites_handler():
            """Handle clearing all sites"""
            sites_display, site_choices, status_msg = site_manager.clear_sites()
            
            return (
                sites_display,
                gr.Radio(choices=[], visible=False, show_label=False),
                gr.Button(visible=False),
                status_msg,
                generate_config_summary()
            )
        
        # Generic handlers for projects, workbooks, datasources, flows
        def create_add_handler(manager):
            def handler(luid, scope):
                display, choices, status = manager.add_resource(luid, scope)
                visible = bool(manager.resources)
                return (
                    display,
                    gr.Radio(choices=choices, visible=visible, show_label=False),
                    gr.Button(visible=visible),
                    status,
                    generate_config_summary()
                )
            return handler
        
        def create_delete_handler(manager):
            def handler(selected):
                display, choices, status = manager.delete_resource(selected)
                visible = bool(manager.resources)
                return (
                    display,
                    gr.Radio(choices=choices, visible=visible, show_label=False),
                    gr.Button(visible=visible),
                    status,
                    generate_config_summary()
                )
            return handler
        
        def create_clear_handler(manager):
            def handler():
                display, choices, status = manager.clear_resources()
                return (
                    display,
                    gr.Radio(choices=[], visible=False, show_label=False),
                    gr.Button(visible=False),
                    status,
                    generate_config_summary()
                )
            return handler
        
        def toggle_tenant_inputs(enable, tenant_id):
            """Show/hide tenant inputs and populate tenant LUID"""
            return (
                gr.Textbox(value=tenant_id, visible=enable),
                gr.Dropdown(visible=enable),
                gr.Button(visible=enable),    # Add button
                gr.Button(visible=enable),    # Clear button
                gr.HTML(visible=enable),      # Display
                generate_config_summary()
            )
        
        def add_tenant_handler(tenant_luid, tenant_scope_val):
            """Handle adding tenant scope"""
            display, choices, status = tenant_manager.add_resource(tenant_luid, tenant_scope_val)
            visible = bool(tenant_manager.resources)
            return (
                display,
                gr.Radio(choices=choices, visible=visible, show_label=False),
                gr.Button(visible=visible),
                status,
                generate_config_summary()
            )
        
        def delete_tenant_handler(selected):
            """Handle deleting tenant scope"""
            display, choices, status = tenant_manager.delete_resource(selected)
            visible = bool(tenant_manager.resources)
            return (
                display,
                gr.Radio(choices=choices, visible=visible, show_label=False),
                gr.Button(visible=visible),
                status,
                generate_config_summary()
            )
        
        def clear_tenants_handler():
            """Handle clearing all tenant scopes"""
            display, choices, status = tenant_manager.clear_resources()
            return (
                display,
                gr.Radio(choices=[], visible=False, show_label=False),
                gr.Button(visible=False),
                status,
                generate_config_summary()
            )
        
        def toggle_projects_inputs(enable):
            """Show/hide project inputs"""
            return (
                gr.Textbox(visible=enable),  # LUID input
                gr.Dropdown(visible=enable),  # Scope dropdown
                gr.Button(visible=enable),    # Add button
                gr.Button(visible=enable),    # Clear button
                gr.HTML(visible=enable),      # Display
                generate_config_summary()
            )
        
        def toggle_workbooks_inputs(enable):
            """Show/hide workbook inputs"""
            return (
                gr.Textbox(visible=enable),  # LUID input
                gr.Dropdown(visible=enable),  # Scope dropdown
                gr.Button(visible=enable),    # Add button
                gr.Button(visible=enable),    # Clear button
                gr.HTML(visible=enable),      # Display
                generate_config_summary()
            )
        
        def toggle_datasources_inputs(enable):
            """Show/hide datasource inputs"""
            return (
                gr.Textbox(visible=enable),  # LUID input
                gr.Dropdown(visible=enable),  # Scope dropdown
                gr.Button(visible=enable),    # Add button
                gr.Button(visible=enable),    # Clear button
                gr.HTML(visible=enable),      # Display
                generate_config_summary()
            )
        
        def toggle_flows_inputs(enable):
            """Show/hide flow inputs"""
            return (
                gr.Textbox(visible=enable),  # LUID input
                gr.Dropdown(visible=enable),  # Scope dropdown
                gr.Button(visible=enable),    # Add button
                gr.Button(visible=enable),    # Clear button
                gr.HTML(visible=enable),      # Display
                generate_config_summary()
            )
        
        def generate_config_summary():
            """Generate a summary table of the current configuration"""
            
            # Collect all resources
            all_resources = []
            
            # Add tenants from tenant manager
            for tenant in tenant_manager.resources:
                all_resources.append({
                    "type": "🏢 Tenant",
                    "identifier": "Tenant",
                    "luid": tenant['luid'],
                    "scope": tenant['scope']
                })
            
            # Add sites
            for site in site_manager.sites:
                all_resources.append({
                    "type": "🌐 Site",
                    "identifier": site['site_id'],
                    "luid": site['site_luid'],
                    "scope": site['scope']
                })
            
            # Add projects
            for project in project_manager.resources:
                all_resources.append({
                    "type": "📁 Project",
                    "identifier": "Project",
                    "luid": project['luid'],
                    "scope": project['scope']
                })
            
            # Add workbooks
            for workbook in workbook_manager.resources:
                all_resources.append({
                    "type": "📊 Workbook",
                    "identifier": "Workbook",
                    "luid": workbook['luid'],
                    "scope": workbook['scope']
                })
            
            # Add datasources
            for datasource in datasource_manager.resources:
                all_resources.append({
                    "type": "🗄️ Datasource",
                    "identifier": "Datasource",
                    "luid": datasource['luid'],
                    "scope": datasource['scope']
                })
            
            # Add flows
            for flow in flow_manager.resources:
                all_resources.append({
                    "type": "🔄 Flow",
                    "identifier": "Flow",
                    "luid": flow['luid'],
                    "scope": flow['scope']
                })
            
            if not all_resources:
                return """
                <div style='padding: 20px; background: #f8f9fa; border-radius: 8px; border: 2px dashed #dee2e6; text-align: center;'>
                    <em style='color: #6c757d;'>No resources configured yet. Add resources above to see the configuration summary.</em>
                </div>
                """
            
            # Create table
            html = """
            <div style='padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;'>
                <div style='display: flex; align-items: center; margin-bottom: 15px;'>
                    <strong style='color: #0d6efd; font-size: 1.1em;'>📋 Configuration Summary</strong>
                    <span style='margin-left: auto; color: #6c757d; font-size: 0.9em;'>Total: """ + str(len(all_resources)) + """ resource(s)</span>
                </div>
                <div style='overflow-x: auto;'>
                    <table style='width: 100%; border-collapse: collapse; background: white; border-radius: 6px; overflow: hidden;'>
                        <thead>
                            <tr style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;'>
                                <th style='padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #5a67d8;'>Type</th>
                                <th style='padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #5a67d8;'>Identifier</th>
                                <th style='padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #5a67d8;'>LUID (Resource ID)</th>
                                <th style='padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #5a67d8;'>JWT Scope</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for idx, res in enumerate(all_resources):
                bg_color = '#ffffff' if idx % 2 == 0 else '#f8f9fa'
                html += f"""
                <tr style='background: {bg_color}; transition: background 0.2s;' 
                    onmouseover="this.style.backgroundColor='#e7f1ff'" 
                    onmouseout="this.style.backgroundColor='{bg_color}'">
                    <td style='padding: 12px; border-bottom: 1px solid #e9ecef;'>
                        <strong>{res['type']}</strong>
                    </td>
                    <td style='padding: 12px; border-bottom: 1px solid #e9ecef; color: #495057;'>
                        {res['identifier']}
                    </td>
                    <td style='padding: 12px; border-bottom: 1px solid #e9ecef; font-family: monospace; font-size: 0.85em; color: #6c757d;'>
                        {res['luid']}
                    </td>
                    <td style='padding: 12px; border-bottom: 1px solid #e9ecef;'>
                        <span style='background: #e7f1ff; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: #0d6efd;'>
                            {res['scope']}
                        </span>
                    </td>
                </tr>
                """
            
            html += """
                        </tbody>
                    </table>
                </div>
            </div>
            """
            
            return html

        # --- EVENT HANDLERS ---
        from testing.api_testing import(
             update_curl_commands, 
             test_tcm_connection, 
             test_tableau_connection,
             list_uat_configurations,
             revoke_uat_configuration
        )

        # Site management
        add_site_btn.click(
            fn=add_site_handler,
            inputs=[site_id_input, site_luid_input, site_scope_input],
            outputs=[sites_display, site_selector, delete_site_btn, status_output, config_summary]
        )
        
        delete_site_btn.click(
            fn=delete_site_handler,
            inputs=[site_selector],
            outputs=[sites_display, site_selector, delete_site_btn, status_output, config_summary]
        )
        
        clear_sites_btn.click(
            fn=clear_sites_handler,
            outputs=[sites_display, site_selector, delete_site_btn, status_output, config_summary]
        )
        
        # Tenant management
        enable_tenant.change(
            fn=toggle_tenant_inputs,
            inputs=[enable_tenant, cm_tenant_id],
            outputs=[tenant_luid_display, tenant_scope, add_tenant_btn, clear_tenants_btn, tenants_display, config_summary]
        )
        
        add_tenant_btn.click(
            fn=add_tenant_handler,
            inputs=[tenant_luid_display, tenant_scope],
            outputs=[tenants_display, tenant_selector, delete_tenant_btn, status_output, config_summary]
        )
        
        delete_tenant_btn.click(
            fn=delete_tenant_handler,
            inputs=[tenant_selector],
            outputs=[tenants_display, tenant_selector, delete_tenant_btn, status_output, config_summary]
        )
        
        clear_tenants_btn.click(
            fn=clear_tenants_handler,
            outputs=[tenants_display, tenant_selector, delete_tenant_btn, status_output, config_summary]
        )
        
        # Project management
        enable_projects.change(
            fn=toggle_projects_inputs,
            inputs=[enable_projects],
            outputs=[project_luid, project_scope, add_project_btn, clear_projects_btn, projects_display, config_summary]
        )
        
        add_project_btn.click(
            fn=create_add_handler(project_manager),
            inputs=[project_luid, project_scope],
            outputs=[projects_display, project_selector, delete_project_btn, status_output, config_summary]
        )
        
        delete_project_btn.click(
            fn=create_delete_handler(project_manager),
            inputs=[project_selector],
            outputs=[projects_display, project_selector, delete_project_btn, status_output, config_summary]
        )
        
        clear_projects_btn.click(
            fn=create_clear_handler(project_manager),
            outputs=[projects_display, project_selector, delete_project_btn, status_output, config_summary]
        )
        
        # Workbook management
        enable_workbooks.change(
            fn=toggle_workbooks_inputs,
            inputs=[enable_workbooks],
            outputs=[workbook_luid, workbook_scope, add_workbook_btn, clear_workbooks_btn, workbooks_display, config_summary]
        )
        
        add_workbook_btn.click(
            fn=create_add_handler(workbook_manager),
            inputs=[workbook_luid, workbook_scope],
            outputs=[workbooks_display, workbook_selector, delete_workbook_btn, status_output, config_summary]
        )
        
        delete_workbook_btn.click(
            fn=create_delete_handler(workbook_manager),
            inputs=[workbook_selector],
            outputs=[workbooks_display, workbook_selector, delete_workbook_btn, status_output, config_summary]
        )
        
        clear_workbooks_btn.click(
            fn=create_clear_handler(workbook_manager),
            outputs=[workbooks_display, workbook_selector, delete_workbook_btn, status_output, config_summary]
        )
        
        # Datasource management
        enable_datasources.change(
            fn=toggle_datasources_inputs,
            inputs=[enable_datasources],
            outputs=[datasource_luid, datasource_scope, add_datasource_btn, clear_datasources_btn, datasources_display, config_summary]
        )
        
        add_datasource_btn.click(
            fn=create_add_handler(datasource_manager),
            inputs=[datasource_luid, datasource_scope],
            outputs=[datasources_display, datasource_selector, delete_datasource_btn, status_output, config_summary]
        )
        
        delete_datasource_btn.click(
            fn=create_delete_handler(datasource_manager),
            inputs=[datasource_selector],
            outputs=[datasources_display, datasource_selector, delete_datasource_btn, status_output, config_summary]
        )
        
        clear_datasources_btn.click(
            fn=create_clear_handler(datasource_manager),
            outputs=[datasources_display, datasource_selector, delete_datasource_btn, status_output, config_summary]
        )
        
        # Flow management
        enable_flows.change(
            fn=toggle_flows_inputs,
            inputs=[enable_flows],
            outputs=[flow_luid, flow_scope, add_flow_btn, clear_flows_btn, flows_display, config_summary]
        )
        
        add_flow_btn.click(
            fn=create_add_handler(flow_manager),
            inputs=[flow_luid, flow_scope],
            outputs=[flows_display, flow_selector, delete_flow_btn, status_output, config_summary]
        )
        
        delete_flow_btn.click(
            fn=create_delete_handler(flow_manager),
            inputs=[flow_selector],
            outputs=[flows_display, flow_selector, delete_flow_btn, status_output, config_summary]
        )
        
        clear_flows_btn.click(
            fn=create_clear_handler(flow_manager),
            outputs=[flows_display, flow_selector, delete_flow_btn, status_output, config_summary]
        )

            
        def run_uat_workflow(cm_tenant_id, cm_pat_secret, cm_pat_login_url, cm_jwt_login_url, cm_uat_configs_url,
                            tc_pod_url, tc_username, 
                            jwt_issuer, jwt_expiration, uat_config_name):
            """
            Run the complete UAT configuration workflow.
            
            Args:
                Various configuration parameters
                
            Yields:
                Status messages and results
            """
            
            os.environ.update({
                "CLOUD_MANAGER_TENANT_ID": cm_tenant_id, "CLOUD_MANAGER_PAT_SECRET": cm_pat_secret,
                "CLOUD_MANAGER_PAT_LOGIN_URL": cm_pat_login_url, "CLOUD_MANAGER_UAT_CONFIGS_URL": cm_uat_configs_url,
                "TABLEAU_CLOUD_POD_URL": tc_pod_url,
                "TABLEAU_CLOUD_USERNAME": tc_username,
                "JWT_ISSUER": jwt_issuer, "CLOUD_MANAGER_JWT_LOGIN_URL": cm_jwt_login_url
            })

            results = {}
            generated_jwt = ""
            private_key_path = None
            public_key_path = None
            
            # Build resource IDs and scopes from managers
            resource_ids = []
            final_scopes = []
            
            # Collect all resources from managers
            for tenant in tenant_manager.resources:
                resource_ids.append(tenant['luid'])
                final_scopes.append(tenant['scope'])
            
            for site in site_manager.sites:
                resource_ids.append(site['site_luid'])
                final_scopes.append(site['scope'])
            
            for project in project_manager.resources:
                resource_ids.append(project['luid'])
                final_scopes.append(project['scope'])
            
            for workbook in workbook_manager.resources:
                resource_ids.append(workbook['luid'])
                final_scopes.append(workbook['scope'])
            
            for datasource in datasource_manager.resources:
                resource_ids.append(datasource['luid'])
                final_scopes.append(datasource['scope'])
            
            for flow in flow_manager.resources:
                resource_ids.append(flow['luid'])
                final_scopes.append(flow['scope'])
            
            # Fallback to default if nothing selected
            if not final_scopes:
                final_scopes = []
                resource_ids = []
                #if site_manager.sites:
                #    resource_ids = [site_manager.sites[0]['site_luid']]
                #else:
                #    resource_ids = []

            def get_file_components():
                if private_key_path and public_key_path:
                    return gr.File(value=private_key_path, visible=True), gr.File(value=public_key_path, visible=True)
                else:
                    return gr.File(visible=False), gr.File(visible=False)
            
            try:
                # Step 1
                yield "Step 1: Generating RSA key pair...", {**results}, *get_file_components()
                key_paths = generate_key_pair()
                private_key_path = key_paths['private_key_path']
                public_key_path = key_paths['public_key_path']
                results["key_generation"] = {"status": "success", "paths": key_paths}
                yield "✅ Step 1: RSA key pair generated successfully. Download links are available below.", results, *get_file_components()

                # Step 2
                yield "Step 2: Logging into Cloud Manager with PAT...", results, *get_file_components()
                session_token = login_cloud_manager_pat()
                results["pat_login"] = {"status": "success", "token": session_token[:20] + "..."}
                yield "✅ Step 2: Successfully logged into Cloud Manager with PAT", results, *get_file_components()
                
                # Step 3 - Create UAT config with resource IDs
                yield "Step 3: Creating UAT configuration with resource access...", results, *get_file_components()
                
                # Note: You'll need to update create_uat_config to accept resource_ids
                # For now, we'll pass the scopes as before, but show resource_ids in results
                success, uat_result = create_uat_config(session_token, final_scopes, uat_config_name, resource_ids)
                
                # Add resource IDs to the result for visibility
                uat_result["resource_ids"] = resource_ids
                results["uat_config"] = uat_result
                
                if success:
                    yield f"✅ Step 3: UAT configuration '{uat_config_name}' created with {len(resource_ids)} resource(s)", results, *get_file_components()
                else:
                    error_msg = f"❌ Step 3 Failed: {uat_result.get('message', 'Unknown error')}"
                    results["uat_config"]["error"] = True
                    yield error_msg, results, *get_file_components()
                    return

                # Step 4 - Generate JWT with custom expiration and scopes
                yield f"Step 4: Generating JWT (valid for {jwt_expiration} minutes, {len(final_scopes)} scope(s))...", results, *get_file_components()
                
                from auth.jwt_builder import build_jwt

                generated_jwt = build_jwt(jwt_issuer, jwt_expiration, cm_tenant_id, tc_username, final_scopes)

                results["jwt"] = {
                    "status": "success", 
                    "token": generated_jwt,
                    "expiration_minutes": jwt_expiration,
                    "scopes": final_scopes
                }

                yield f"✅ Step 4: JWT generated successfully (expires in {jwt_expiration} minutes)", results, *get_file_components()

                
                # Step 5
                yield "Step 5: Testing TCM API login with JWT...", results, *get_file_components()
                tcm_token = login_tcm_with_jwt(jwt_token=generated_jwt)
                results["tcm_login"] = {"status": "success", "token": tcm_token[:20] + "..."}
                results["curl_commands"] = {
                        "tcm": f"curl -X POST '{cm_jwt_login_url}' -H 'Content-Type: application/json' -d '{{\"token\": \"{generated_jwt}\"}}'"
                        }
                
                yield "✅ Step 5: TCM API login with JWT successful", results, *get_file_components()

            except Exception as e:
                error_msg = f"❌ Unexpected Error: {str(e)}"
                results["error"] = str(e)
                yield error_msg, results, *get_file_components()

                # Step 6
                
                # Use the first site for testing
                # Only test Tableau login if sites are configured
            try:
                if site_manager.sites:
                    yield "Step 6: Testing Tableau REST API login with JWT...", results, *get_file_components()
                    site_id = site_manager.sites[0]['site_id']
                    tableau_token = login_tableau_cloud(jwt_token=generated_jwt, site_id=site_id)
                    results["tableau_login"] = {"status": "success", "token": tableau_token[:20] + "..."}
                    results["debug_info"] = {
                    "decoded_payload": pyjwt.decode(generated_jwt, options={"verify_signature": False}),
                    "request_body_sent": {"credentials": {"jwt": f"{generated_jwt[:50]}...", "isUat": True, "site": {"contentUrl": site_id if site_manager.sites else "N/A"}}}
                    }
                    results["curl_commands"].update({
                        "tableau": f"curl -X POST '{tc_pod_url}/api/3.27/auth/signin' -H 'Content-Type: application/json' -d '{{\"credentials\": {{\"jwt\": \"{generated_jwt}\", \"isUat\": true, \"site\": {{\"contentUrl\": \"{site_id}\"}}}}}}'"
                    })
                else:
                    results["tableau_login"] = {"status": "skipped", "message": "No sites configured"}
                                
                yield "✅ Workflow completed successfully! Check the 'Detailed Results' and 'Testing' tabs.", results, *get_file_components()

            except Exception as e:
                error_msg = f"❌ Unexpected Error: {str(e)}"
                results["error"] = str(e)
                yield error_msg, results, *get_file_components()

        start_btn.click(
            fn=run_uat_workflow,
            inputs=[cm_tenant_id, cm_pat_secret, cm_pat_login_url, cm_jwt_login_url, cm_uat_configs_url,
                    tc_pod_url, tc_username, 
                    jwt_issuer, jwt_expiration, uat_config_name],
            outputs=[status_output, result_output, private_key_file, public_key_file]
        ).then(
            fn=update_curl_commands,
            inputs=[result_output],
            outputs=[tcm_curl, tc_curl]
        )
        
        test_tcm_btn.click(fn=test_tcm_connection, inputs=[cm_jwt_login_url, result_output], outputs=[test_tcm_output])
        test_tc_btn.click(fn=test_tableau_connection, inputs=[tc_pod_url, result_output], outputs=[test_tc_output])
        
        def handle_list_configs(cm_pat_secret, cm_pat_login_url, cm_uat_configs_url):
            """List configurations and prepare selector"""
            configs_data, curl_cmd, config_ids = list_uat_configurations(cm_pat_secret, cm_pat_login_url, cm_uat_configs_url)
            has_configs = len(config_ids) > 0
            return (
                configs_data,
                curl_cmd,
                gr.Radio(choices=config_ids, visible=has_configs, show_label=True),
                gr.Button(visible=has_configs)
            )
        
        list_configs_btn.click(
            fn=handle_list_configs,
            inputs=[cm_pat_secret, cm_pat_login_url, cm_uat_configs_url],
            outputs=[configs_output, configs_curl, config_selector, revoke_config_btn]
        )
        
        def handle_revoke(config_id, cm_pat_secret, cm_pat_login_url, cm_uat_configs_url):
            """Handle configuration revocation"""
            result, curl_cmd = revoke_uat_configuration(config_id, cm_pat_secret, cm_pat_login_url, cm_uat_configs_url)
            
            return (
                result,
                curl_cmd,
                gr.Accordion(visible=True)
            )
        
        revoke_config_btn.click(
            fn=handle_revoke,
            inputs=[config_selector, cm_pat_secret, cm_pat_login_url, cm_uat_configs_url],
            outputs=[revoke_output, revoke_curl, revoke_curl_accordion]
        ).then(
            fn=lambda: gr.JSON(visible=True),
            outputs=[revoke_output]
        )

    return app

if __name__ == "__main__":
    if not os.path.exists("keys"): os.makedirs("keys")
    app = create_uat_config_tool()
    app.launch(share=False, theme=gr.themes.Soft())