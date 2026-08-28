"""Streamlit 前端 - 素材整理与文案生成"""
import streamlit as st
import requests
import json
import sys
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, '.')

# 配置
BACKEND_URL = st.secrets.get("backend", {}).get("url", "http://localhost:8000")

# 导入飞书写入器（用于读取表格数据）
try:
    from src.feishu_writer import FeishuWriter
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False

st.set_page_config(page_title="梦想盒子素材整理", layout="wide")

# ============ 初始化 Session State ============
if "materials" not in st.session_state:
    st.session_state.materials = []
if "evaluations" not in st.session_state:
    st.session_state.evaluations = []
if "generated_copy" not in st.session_state:
    st.session_state.generated_copy = None


# ============ 辅助函数 ============

def check_backend_health():
    """检查后端服务是否可用"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        return resp.json()
    except:
        return None


def load_materials_from_json(json_str: str) -> List[Dict]:
    """从 JSON 字符串加载素材"""
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
        return []
    except:
        return []


# ============ 页面渲染 ============

def main():
    st.title("🎨 梦想盒子素材整理与文案生成")
    
    # 检查后端状态
    health = check_backend_health()
    if health:
        ai_status = "✅ AI 已启用" if health.get("ai_enabled") else "️ AI 未启用"
        st.sidebar.success(f"后端服务正常 | {ai_status}")
    else:
        st.sidebar.error("❌ 后端服务未连接")
        st.warning("请先启动后端服务：`python -m backend.main`")
        return
    
    # 侧边栏：配置
    with st.sidebar:
        st.subheader("飞书配置")
        
        # 飞书凭证配置
        feishu_app_id = st.text_input("飞书应用 App ID", value=st.secrets.get("feishu", {}).get("app_id", ""))
        feishu_app_secret = st.text_input("飞书应用 App Secret", value=st.secrets.get("feishu", {}).get("app_secret", ""), type="password")
        feishu_app_token = st.text_input("飞书表格 App Token", value=st.secrets.get("feishu", {}).get("app_token", ""))
        feishu_table_id = st.text_input("飞书表格 Table ID", value=st.secrets.get("feishu", {}).get("table_id", ""))
        
        # 测试连接按钮
        if st.button("🔌 测试飞书连接", use_container_width=True):
            if FEISHU_AVAILABLE and feishu_app_id and feishu_app_secret and feishu_app_token and feishu_table_id:
                try:
                    writer = FeishuWriter(
                        app_id=feishu_app_id,
                        app_secret=feishu_app_secret,
                        app_token=feishu_app_token,
                        table_id=feishu_table_id
                    )
                    # 尝试读取一条数据测试
                    records = writer.read_records(limit=1)
                    if records is not None:
                        st.success("✅ 飞书连接成功！")
                    else:
                        st.error("❌ 连接失败：无法读取数据")
                except Exception as e:
                    st.error(f"❌ 连接失败：{str(e)}")
            else:
                st.warning("⚠️ 请先填写完整的飞书配置")
        
        st.divider()
        
        st.subheader("筛选条件")
        
        # 学校筛选
        schools_input = st.text_area(
            "学校名称（每行一个，留空表示全部）",
            height=100
        )
        
        # 时间范围
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=None)
        with col2:
            end_date = st.date_input("结束日期", value=None)
        
        # 素材类型
        material_type = st.selectbox(
            "素材类型",
            ["图文混合", "纯图片", "纯文字", "全部"]
        )
        
        # 内容长度
        min_length = st.slider("最小内容长度（字）", 0, 500, 50)
        
        st.divider()
        
        # 从飞书表格导入
        st.subheader("📥 从飞书表格导入")
        st.info("配置飞书凭证后，可以自动从飞书多维表格读取素材数据")
        
        feishu_app_id = st.text_input("飞书应用 App ID", "", type="password", key="feishu_app_id")
        feishu_app_secret = st.text_input("飞书应用 App Secret", "", type="password", key="feishu_app_secret")
        feishu_app_token = st.text_input("飞书表格 App Token", "", key="feishu_app_token")
        feishu_table_id = st.text_input("飞书表格 Table ID", "", key="feishu_table_id")
        
        if st.button("📥 从飞书表格导入素材", type="primary", use_container_width=True):
            if not all([feishu_app_id, feishu_app_secret, feishu_app_token, feishu_table_id]):
                st.error("请填写所有飞书配置项")
            else:
                with st.spinner("正在从飞书表格读取数据..."):
                    try:
                        # 获取访问令牌
                        token_resp = requests.post(
                            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                            json={"app_id": feishu_app_id, "app_secret": feishu_app_secret},
                            timeout=10
                        )
                        if token_resp.status_code != 200:
                            st.error(f"获取访问令牌失败：{token_resp.text}")
                        else:
                            token = token_resp.json().get("tenant_access_token")
                            if not token:
                                st.error(f"获取访问令牌失败：{token_resp.json()}")
                            else:
                                # 读取表格数据
                                headers = {"Authorization": f"Bearer {token}"}
                                data_resp = requests.get(
                                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu_app_token}/tables/{feishu_table_id}/records?page_size=100",
                                    headers=headers,
                                    timeout=30
                                )
                                if data_resp.status_code != 200:
                                    st.error(f"读取表格数据失败：{data_resp.text}")
                                else:
                                    data = data_resp.json()
                                    items = data.get("data", {}).get("items", [])
                                    if not items:
                                        st.warning("表格中没有数据")
                                    else:
                                        # 转换为素材格式
                                        materials = []
                                        for item in items:
                                            fields = item.get("fields", {})
                                            materials.append({
                                                "feed_id": str(fields.get("动态 ID", fields.get("动态 ID", ""))),
                                                "text": fields.get("正文内容", fields.get("正文内容", "")),
                                                "school": fields.get("来源学校", fields.get("来源学校", "")),
                                                "author": fields.get("发布者", fields.get("发布者", "")),
                                                "publish_time": fields.get("发布时间", fields.get("发布时间", "")),
                                                "image_count": int(fields.get("图片数量", fields.get("图片数量", 0)) or 0),
                                                "material_type": fields.get("素材类型", fields.get("素材类型", "图文混合")),
                                            })
                                        
                                        st.session_state.materials = materials
                                        st.session_state.all_materials = materials.copy()
                                        st.success(f"成功导入 {len(materials)} 条素材")
                                        st.rerun()
                    except Exception as e:
                        st.error(f"导入失败：{str(e)}")
        
        st.divider()
        
        # 成篇模式
        st.subheader("成篇模式")
        mode = st.radio(
            "选择成篇方式",
            ["single", "same_school", "cross_school"],
            format_func=lambda x: {
                "single": "📝 单条成篇",
                "same_school": " 同校成篇",
                "cross_school": "🌐 跨校成篇"
            }[x]
        )
        
        # 项目类型
        project_type = st.text_input("项目类型（可选）", "")
        
        st.divider()
        
        # 高级设置
        st.subheader("高级设置")
        max_iterations = st.slider("最大迭代次数", 1, 5, 3, help="迭代次数越多，文案质量可能越高，但耗时更长")
        
        st.divider()
        
        # 从飞书表格读取数据
        st.subheader("📊 从飞书表格读取数据")
        
        feishu_app_id = st.text_input("飞书应用 App ID", value=st.secrets.get("feishu", {}).get("app_id", ""), type="password")
        feishu_app_secret = st.text_input("飞书应用 App Secret", value=st.secrets.get("feishu", {}).get("app_secret", ""), type="password")
        feishu_app_token = st.text_input("飞书表格 App Token", value=st.secrets.get("feishu", {}).get("app_token", ""))
        feishu_table_id = st.text_input("飞书表格 Table ID", value=st.secrets.get("feishu", {}).get("table_id", ""))
        
        col_read, col_test = st.columns(2)
        with col_read:
            read_from_feishu = st.button("📥 从飞书表格读取数据", type="primary")
        with col_test:
            test_connection = st.button("🔌 测试连接")
        
        if test_connection:
            if feishu_app_id and feishu_app_secret and feishu_app_token and feishu_table_id:
                try:
                    # 测试连接
                    import requests
                    resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", json={
                        "app_id": feishu_app_id,
                        "app_secret": feishu_app_secret
                    })
                    if resp.status_code == 200 and resp.json().get("tenant_access_token"):
                        st.success("✅ 飞书连接成功！")
                    else:
                        st.error("❌ 连接失败：凭证错误")
                except Exception as e:
                    st.error(f"❌ 连接失败：{e}")
            else:
                st.warning("⚠️ 请先填写飞书凭证")
        
        if read_from_feishu:
            if feishu_app_id and feishu_app_secret and feishu_app_token and feishu_table_id:
                try:
                    with st.spinner("正在从飞书表格读取数据..."):
                        import requests
                        
                        # 获取访问令牌
                        resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", json={
                            "app_id": feishu_app_id,
                            "app_secret": feishu_app_secret
                        })
                        token = resp.json().get("tenant_access_token")
                        
                        if not token:
                            st.error("❌ 获取访问令牌失败")
                        else:
                            # 读取表格数据
                            headers = {"Authorization": f"Bearer {token}"}
                            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu_app_token}/tables/{feishu_table_id}/records?page_size=500"
                            resp = requests.get(url, headers=headers)
                            
                            if resp.status_code == 200:
                                data = resp.json().get("data", {})
                                items = data.get("items", []) or []
                                
                                # 转换为素材格式
                                materials = []
                                for item in items:
                                    fields = item.get("fields", {})
                                    material = {
                                        "feed_id": str(fields.get("动态 ID", fields.get("动态 ID", ""))),
                                        "text": str(fields.get("正文内容", fields.get("正文内容", ""))),
                                        "school": str(fields.get("来源学校", fields.get("来源学校", ""))),
                                        "author": str(fields.get("发布者", fields.get("发布者", ""))),
                                        "publish_time": str(fields.get("发布时间", fields.get("发布时间", ""))),
                                        "image_count": int(fields.get("图片数量", fields.get("图片数量", 0)) or 0),
                                        "material_type": str(fields.get("素材类型", fields.get("素材类型", "图文混合"))),
                                        "images": []
                                    }
                                    if material["text"].strip():
                                        materials.append(material)
                                
                                st.session_state.materials = materials
                                st.success(f"✅ 成功读取 {len(materials)} 条素材！")
                            else:
                                st.error(f"❌ 读取失败：{resp.text}")
                except Exception as e:
                    st.error(f"❌ 读取失败：{e}")
            else:
                st.warning("⚠️ 请先填写飞书凭证")
    
    # 主区域：素材输入
    st.subheader("📥 素材输入")
    
    tab1, tab2 = st.tabs(["手动输入", "批量导入"])
    
    with tab1:
        # 单条素材输入
        with st.form("material_form"):
            col1, col2 = st.columns(2)
            with col1:
                feed_id = st.text_input("动态 ID")
                school = st.text_input("来源学校")
                author = st.text_input("发布者")
            with col2:
                publish_time = st.text_input("发布时间")
                image_count = st.number_input("图片数量", 0, 100, 0)
                material_type_input = st.selectbox(
                    "素材类型",
                    ["图文混合", "纯图片", "纯文字"],
                    key="form_type"
                )
            
            text = st.text_area("正文内容", height=150)
            
            submitted = st.form_submit_button("➕ 添加素材")
            
            if submitted and text.strip():
                material = {
                    "feed_id": feed_id or f"manual_{len(st.session_state.materials)}",
                    "text": text.strip(),
                    "school": school,
                    "author": author,
                    "publish_time": publish_time,
                    "image_count": image_count,
                    "material_type": material_type_input,
                    "images": []
                }
                st.session_state.materials.append(material)
                st.success(f"已添加素材（共 {len(st.session_state.materials)} 条）")
    
    with tab2:
        st.markdown("""
**批量导入格式（JSON）：**
```json
[
  {
    "feed_id": "123456",
    "text": "素材内容...",
    "school": "学校名称",
    "author": "发布者",
    "publish_time": "2025-01-01",
    "image_count": 3,
    "material_type": "图文混合"
  }
]
```
""")
        json_input = st.text_area("粘贴 JSON 数据", height=200)
        
        if st.button(" 导入素材"):
            materials = load_materials_from_json(json_input)
            if materials:
                st.session_state.materials.extend(materials)
                st.success(f"已导入 {len(materials)} 条素材")
            else:
                st.error("JSON 格式错误，请检查")
    
    # 筛选按钮（如果有素材）
    if st.session_state.materials:
        st.divider()
        col_filter1, col_filter2 = st.columns([1, 1])
        with col_filter1:
            if st.button("🔍 应用筛选条件", type="primary", use_container_width=True):
                # 应用筛选条件
                filtered = st.session_state.materials.copy()
                
                # 学校筛选
                if school_names.strip():
                    schools = [s.strip() for s in school_names.strip().split('\n') if s.strip()]
                    filtered = [m for m in filtered if m.get('school', '') in schools]
                
                # 时间筛选
                if start_date:
                    filtered = [m for m in filtered if m.get('publish_time', '') >= start_date]
                if end_date:
                    filtered = [m for m in filtered if m.get('publish_time', '') <= end_date]
                
                # 素材类型筛选
                if material_type_filter != "全部":
                    filtered = [m for m in filtered if m.get('material_type', '') == material_type_filter]
                
                # 字数筛选
                if min_content_length > 0:
                    filtered = [m for m in filtered if len(m.get('text', '')) >= min_content_length]
                
                st.session_state.materials = filtered
                st.success(f"筛选完成，剩余 {len(filtered)} 条素材")
                st.rerun()
        
        with col_filter2:
            if st.button("🔄 重置筛选", use_container_width=True):
                st.session_state.materials = st.session_state.get('all_materials', st.session_state.materials)
                st.success("已重置筛选")
                st.rerun()
    
    # 素材列表
    if st.session_state.materials:
        st.divider()
        st.subheader(f"📋 素材列表（{len(st.session_state.materials)} 条）")
        
        # 显示素材
        for i, mat in enumerate(st.session_state.materials):
            with st.expander(f"素材 {i+1}: {mat.get('school', '未知')} - {mat.get('text', '')[:50]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**动态 ID:** {mat.get('feed_id', 'N/A')}")
                    st.write(f"**学校:** {mat.get('school', 'N/A')}")
                    st.write(f"**发布者:** {mat.get('author', 'N/A')}")
                with col2:
                    st.write(f"**发布时间:** {mat.get('publish_time', 'N/A')}")
                    st.write(f"**图片数量:** {mat.get('image_count', 0)}")
                    st.write(f"**素材类型:** {mat.get('material_type', 'N/A')}")
                
                st.write("**正文内容：**")
                st.write(mat.get('text', ''))
                
                if st.button(f"🗑️ 删除素材 {i+1}", key=f"del_{i}"):
                    st.session_state.materials.pop(i)
                    st.rerun()
        
        # 操作按钮
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 评估素材", use_container_width=True):
                with st.spinner("正在评估素材内容丰富度..."):
                    resp = requests.post(
                        f"{BACKEND_URL}/api/evaluate",
                        json={"materials": st.session_state.materials},
                        timeout=120
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        st.session_state.evaluations = result.get("evaluations", [])
                        st.success(f"评估完成，共 {result.get('count', 0)} 条")
                    else:
                        st.error(f"评估失败：{resp.text}")
        
        with col2:
            if st.button("💡 AI 推荐组合", use_container_width=True):
                if len(st.session_state.materials) < 2:
                    st.warning("至少需要 2 条素材才能推荐组合")
                else:
                    with st.spinner("正在分析素材主题..."):
                        resp = requests.post(
                            f"{BACKEND_URL}/api/recommend",
                            json={
                                "materials": st.session_state.materials,
                                "mode": mode
                            },
                            timeout=120
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                            st.session_state.recommendations = result.get("combinations", [])
                            st.success(f"推荐完成，共 {result.get('count', 0)} 个组合")
                        else:
                            st.error(f"推荐失败：{resp.text}")
        
        with col3:
            if st.button("✨ 生成文案", use_container_width=True):
                if not st.session_state.materials:
                    st.warning("请先添加素材")
                else:
                    with st.spinner(f"正在生成文案（最多迭代{max_iterations}次）..."):
                        resp = requests.post(
                            f"{BACKEND_URL}/api/generate",
                            json={
                                "materials": st.session_state.materials,
                                "mode": mode,
                                "project_type": project_type,
                                "max_iterations": max_iterations
                            },
                            timeout=180
                        )
                        if resp.status_code == 200:
                            st.session_state.generated_copy = resp.json()
                            iterations = resp.json().get("iterations", 0)
                            package_id = resp.json().get("package_id", "")
                            st.success(f"文案生成完成！（迭代{iterations}次，素材包 ID：{package_id}）")
                        else:
                            st.error(f"生成失败：{resp.text}")
    
    # 评估结果
    if st.session_state.evaluations:
        st.divider()
        st.subheader("📊 素材评估结果")
        
        for eval_item in st.session_state.evaluations:
            score = eval_item.get("score", 0)
            can_form = eval_item.get("can_form_story", False)
            
            # 颜色标记
            if score >= 80:
                score_color = "🟢"
            elif score >= 60:
                score_color = ""
            else:
                score_color = "🔴"
            
            with st.expander(f"{score_color} 素材 {eval_item.get('feed_id', 'N/A')} - 评分：{score}"):
                st.write(f"**可成篇：** {'✅ 是' if can_form else '❌ 否'}")
                st.write(f"**推荐类型：** {eval_item.get('recommended_type', 'N/A')}")
                st.write(f"**评分理由：** {eval_item.get('reason', 'N/A')}")
                st.write(f"**建议角度：** {eval_item.get('suggested_angle', 'N/A')}")
    
    # 推荐组合
    if st.session_state.get("recommendations"):
        st.divider()
        st.subheader("💡 AI 推荐组合")
        
        for i, combo in enumerate(st.session_state.recommendations):
            with st.expander(f"组合 {i+1}: {combo.get('theme', '未命名')} (得分：{combo.get('score', 0)})"):
                st.write(f"**主题：** {combo.get('theme', 'N/A')}")
                st.write(f"**推荐理由：** {combo.get('reason', 'N/A')}")
                st.write(f"**包含素材 ID：** {', '.join(combo.get('material_ids', []))}")
                
                if st.button(f"使用此组合生成文案", key=f"use_combo_{i}"):
                    # 筛选出组合中的素材
                    selected_ids = combo.get("material_ids", [])
                    selected_materials = [
                        m for m in st.session_state.materials
                        if m.get("feed_id") in selected_ids
                    ]
                    
                    with st.spinner("正在生成文案..."):
                        resp = requests.post(
                            f"{BACKEND_URL}/api/generate",
                            json={
                                "materials": selected_materials,
                                "mode": mode,
                                "project_type": project_type
                            },
                            timeout=120
                        )
                        if resp.status_code == 200:
                            st.session_state.generated_copy = resp.json()
                            st.success("文案生成完成！")
    
    # 批量生成
    st.divider()
    st.subheader("🚀 批量生成")
    st.markdown("""
    **批量生成说明：**
    - 自动为每条可成篇的素材生成文案
    - 同校素材自动组合成素材包
    - 适合快速处理大量素材
    """)
    
    if st.button("🚀 批量生成所有可成篇素材", use_container_width=True):
        if not st.session_state.evaluations:
            st.warning("请先评估素材")
        else:
            # 筛选可成篇的素材
            can_form_ids = [
                e.get("feed_id") for e in st.session_state.evaluations
                if e.get("can_form_story", False)
            ]
            
            can_form_materials = [
                m for m in st.session_state.materials
                if m.get("feed_id") in can_form_ids
            ]
            
            if not can_form_materials:
                st.warning("没有可成篇的素材")
            else:
                st.info(f"找到 {len(can_form_materials)} 条可成篇素材，开始批量生成...")
                
                # 按学校分组
                school_groups = {}
                for m in can_form_materials:
                    school = m.get("school", "未知")
                    if school not in school_groups:
                        school_groups[school] = []
                    school_groups[school].append(m)
                
                # 批量生成
                batch_results = []
                progress = st.progress(0)
                total = len(school_groups)
                
                for idx, (school, materials) in enumerate(school_groups.items()):
                    progress.progress((idx + 1) / total)
                    
                    # 确定模式
                    if len(materials) > 1:
                        gen_mode = "same_school"
                    else:
                        gen_mode = "single"
                    
                    # 生成文案
                    resp = requests.post(
                        f"{BACKEND_URL}/api/generate",
                        json={
                            "materials": materials,
                            "mode": gen_mode,
                            "project_type": project_type,
                            "max_iterations": max_iterations
                        },
                        timeout=180
                    )
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        batch_results.append({
                            "school": school,
                            "mode": gen_mode,
                            "count": len(materials),
                            "package_id": result.get("package_id", ""),
                            "title": result.get("title", ""),
                            "success": True
                        })
                    else:
                        batch_results.append({
                            "school": school,
                            "mode": gen_mode,
                            "count": len(materials),
                            "success": False,
                            "error": resp.text
                        })
                
                st.session_state.batch_results = batch_results
                st.success(f"批量生成完成！共 {len(batch_results)} 个素材包")
    
    # 显示批量生成结果
    if st.session_state.get("batch_results"):
        st.divider()
        st.subheader(" 批量生成结果")
        
        for i, result in enumerate(st.session_state.batch_results):
            if result.get("success"):
                st.success(f"✅ {result['school']} - {result['count']}条素材 - {result['mode']} - 素材包：{result['package_id']}")
                st.markdown(f"   标题：{result.get('title', 'N/A')}")
            else:
                st.error(f"❌ {result['school']} - 生成失败：{result.get('error', '未知错误')}")
    
    # 生成的文案
    if st.session_state.generated_copy:
        st.divider()
        st.subheader("📝 生成的文案")
        
        copy = st.session_state.generated_copy
        
        # 素材包信息
        package_id = copy.get("package_id", "")
        iterations = copy.get("iterations", 0)
        if package_id:
            st.info(f"📦 素材包 ID：{package_id} | 迭代次数：{iterations}")
        
        # 标题
        st.markdown(f"### {copy.get('title', '无标题')}")
        
        # 摘要
        st.markdown(f"**摘要：** {copy.get('summary', '无摘要')}")
        
        # 完整文案
        st.markdown("**完整文案：**")
        st.markdown(copy.get('content', '无内容'))
        
        # 元信息
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**涉及人物：**")
            for person in copy.get('people', []):
                st.markdown(f"- {person}")
        
        with col2:
            st.markdown("**涉及学校：**")
            for school in copy.get('schools', []):
                st.markdown(f"- {school}")
        
        st.markdown("**挖掘的价值点：**")
        for value in copy.get('values', []):
            st.markdown(f"- {value}")
        
        # 操作按钮
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 复制文案", use_container_width=True):
                st.code(copy.get('content', ''), language="text")
                st.info("文案已显示在上方代码块中，可手动复制")
        
        with col2:
            if st.button(" 导出为 JSON", use_container_width=True):
                json_str = json.dumps(copy, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载 JSON",
                    data=json_str,
                    file_name="generated_copy.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button(" 导出为 Markdown", use_container_width=True):
                md_content = f"# {copy.get('title', '无标题')}\n\n"
                md_content += f"**摘要：** {copy.get('summary', '无摘要')}\n\n"
                md_content += f"**素材包 ID：** {package_id}\n\n"
                md_content += f"**迭代次数：** {iterations}\n\n"
                md_content += "---\n\n"
                md_content += copy.get('content', '无内容')
                md_content += "\n\n---\n\n**涉及人物：**\n"
                for person in copy.get('people', []):
                    md_content += f"- {person}\n"
                md_content += "\n**涉及学校：**\n"
                for school in copy.get('schools', []):
                    md_content += f"- {school}\n"
                md_content += "\n**挖掘的价值点：**\n"
                for value in copy.get('values', []):
                    md_content += f"- {value}\n"
                
                st.download_button(
                    label="下载 Markdown",
                    data=md_content,
                    file_name="generated_copy.md",
                    mime="text/markdown"
                )
        
        with col4:
            if st.button(" 重新生成", use_container_width=True):
                st.session_state.generated_copy = None
                st.rerun()


if __name__ == "__main__":
    main()
