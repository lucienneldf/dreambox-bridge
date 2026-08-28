"""
AI 素材处理服务
封装素材筛选和文案生成功能
"""
import os
import re
from typing import Dict, List, Optional
from src.llm_client import llm_client


class MaterialProcessor:
    """素材处理器"""
    
    def __init__(self):
        self.skill1_path = "assets/SKILL（素材筛选）.md"
        self.skill2_path = "assets/SKILL（文案生成）.md"
        self._skill1_content = None
        self._skill2_content = None
    
    def _load_skill(self, skill_path: str) -> str:
        """加载 Skill 文档"""
        if os.path.exists(skill_path):
            with open(skill_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    @property
    def skill1_content(self) -> str:
        """获取 Skill 1 内容（懒加载）"""
        if self._skill1_content is None:
            self._skill1_content = self._load_skill(self.skill1_path)
        return self._skill1_content
    
    @property
    def skill2_content(self) -> str:
        """获取 Skill 2 内容（懒加载）"""
        if self._skill2_content is None:
            self._skill2_content = self._load_skill(self.skill2_path)
        return self._skill2_content
    
    def format_material(self, feed: Dict) -> str:
        """格式化素材为文本"""
        parts = []
        
        if feed.get("feed_id"):
            parts.append(f"动态ID: {feed['feed_id']}")
        if feed.get("school_name"):
            parts.append(f"来源学校: {feed['school_name']}")
        if feed.get("pub_time"):
            parts.append(f"发布时间: {feed['pub_time']}")
        if feed.get("author"):
            parts.append(f"发布者: {feed['author']}")
        if feed.get("text_content"):
            parts.append(f"正文内容:\n{feed['text_content']}")
        if feed.get("material_type"):
            parts.append(f"素材类型: {feed['material_type']}")
        if feed.get("word_tier"):
            parts.append(f"字数档位: {feed['word_tier']}")
        
        return "\n".join(parts)
    
    def parse_grade_result(self, result_text: str) -> Dict:
        """解析筛选结果"""
        parsed = {
            "grade": "",
            "analysis": "",
            "notes": "",
            "raw": result_text
        }
        
        # 提取质量等级
        grade_match = re.search(r'【质量等级】\s*(S1|S2|S3|S4|S2-)', result_text)
        if grade_match:
            parsed["grade"] = grade_match.group(1)
        
        # 提取判定依据
        analysis_match = re.search(r'【判定依据.*?】\s*(.*?)【注意点】', result_text, re.DOTALL)
        if analysis_match:
            parsed["analysis"] = analysis_match.group(1).strip()
        
        # 提取注意点
        notes_match = re.search(r'【注意点】\s*(.*)', result_text, re.DOTALL)
        if notes_match:
            parsed["notes"] = notes_match.group(1).strip()
        
        return parsed
    
    def parse_copy_result(self, result_text: str) -> Dict:
        """解析文案生成结果"""
        parsed = {
            "title": "",
            "summary": "",
            "content": "",
            "thanks": "",
            "notes": "",
            "raw": result_text
        }
        
        # 提取标题
        title_match = re.search(r'【标题】\s*(.*?)(?=【|$)', result_text, re.DOTALL)
        if title_match:
            parsed["title"] = title_match.group(1).strip()
        
        # 提取摘要
        summary_match = re.search(r'【摘要】\s*(.*?)(?=【|$)', result_text, re.DOTALL)
        if summary_match:
            parsed["summary"] = summary_match.group(1).strip()
        
        # 提取正文
        content_match = re.search(r'【正文】\s*(.*?)(?=【|$)', result_text, re.DOTALL)
        if content_match:
            parsed["content"] = content_match.group(1).strip()
        
        # 提取感谢语
        thanks_match = re.search(r'【感谢语】\s*(.*?)(?=【|$)', result_text, re.DOTALL)
        if thanks_match:
            parsed["thanks"] = thanks_match.group(1).strip()
        
        # 提取成稿说明
        notes_match = re.search(r'【成稿说明】\s*(.*)', result_text, re.DOTALL)
        if notes_match:
            parsed["notes"] = notes_match.group(1).strip()
        
        return parsed
    
    def grade_material(self, feed: Dict) -> Dict:
        """筛选单条素材"""
        material_text = self.format_material(feed)
        
        try:
            result = llm_client.grade_material(material_text, self.skill1_content)
            parsed = self.parse_grade_result(result)
            parsed["success"] = True
            return parsed
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "grade": "",
                "analysis": "",
                "notes": "",
                "raw": ""
            }
    
    def grade_materials(self, feeds: List[Dict], progress_callback=None) -> List[Dict]:
        """批量筛选素材"""
        results = []
        total = len(feeds)
        
        for i, feed in enumerate(feeds):
            result = self.grade_material(feed)
            result["feed_id"] = feed.get("feed_id", "")
            result["school_name"] = feed.get("school_name", "")
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results
    
    def generate_copy(self, feed: Dict, grade_result: Dict, similar_cases: Optional[List[Dict]] = None) -> Dict:
        """生成单篇文案"""
        material_text = self.format_material(feed)
        grade_text = f"""质量等级：{grade_result.get('grade', '')}
判定依据：{grade_result.get('analysis', '')}
注意点：{grade_result.get('notes', '')}"""
        
        try:
            # 如果有相似案例，组装到提示词中
            if similar_cases and len(similar_cases) > 0:
                cases_text = "\n\n".join([
                    f"### 案例{i+1}（相似度：{case.get('similarity', 0):.0%}）\n"
                    f"学校：{case.get('school_name', '')}\n"
                    f"原始素材：{case.get('original_text', '')[:200]}...\n\n"
                    f"参考文案：\n{case.get('published_copy') or case.get('generated_copy', '')}"
                    for i, case in enumerate(similar_cases)
                ])
                
                skill_with_cases = f"""{self.skill2_content}

---

## 相似案例参考（请学习这些案例的风格和结构）

{cases_text}

---

请根据以上要求，参考相似案例的风格，为当前素材生成文案。"""
            else:
                skill_with_cases = self.skill2_content
            
            result = llm_client.generate_copy(
                material_text, 
                grade_text, 
                skill_with_cases
            )
            parsed = self.parse_copy_result(result)
            parsed["success"] = True
            parsed["feed_id"] = feed.get("feed_id", "")
            return parsed
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "title": "",
                "summary": "",
                "content": "",
                "thanks": "",
                "notes": "",
                "raw": "",
                "feed_id": feed.get("feed_id", "")
            }
    
    def generate_copies(self, feeds_with_grades: List[Dict], 
                        progress_callback=None) -> List[Dict]:
        """批量生成文案"""
        results = []
        total = len(feeds_with_grades)
        
        for i, item in enumerate(feeds_with_grades):
            feed = item.get("feed", {})
            grade = item.get("grade", {})
            
            result = self.generate_copy(feed, grade)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results


# 全局实例
material_processor = MaterialProcessor()
