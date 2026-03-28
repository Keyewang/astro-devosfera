import datetime

def ensure_datetime(val):
    if isinstance(val, (datetime.datetime, datetime.date)):
        if isinstance(val, datetime.datetime):
            return val
        return datetime.datetime.combine(val, datetime.time.min)
    if isinstance(val, str):
        val = val.strip("'\" ")
        try:
            if 'T' in val:
                # 处理 ISO 格式
                normalized = val.replace('Z', '+00:00')
                return datetime.fromisoformat(normalized)
            return datetime.strptime(val, '%Y-%m-%d')
        except:
            pass
    return val

def transform_toggle(match):
    # 提取标题和内容
    title_raw = match.group(1).strip()
    content = match.group(2).strip()
    
    # 提取引号内的标题，如果没有引号则取原始值
    title_match = re.search(r'"(.*?)"', title_raw)
    title = title_match.group(1) if title_match else title_raw
    
    return f"""
<div className="border-l-4 border-accent bg-accent/8 p-6 my-8 rounded-r-xl">
  <h4 className="font-bold text-foreground text-base m-0 mb-3 flex items-center gap-2">
    <svg className="w-5 h-5 text-accent shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path></svg>
    {title}
  </h4>
  <div className="text-foreground/75 text-sm m-0 leading-relaxed">

{content}

  </div>
</div>
"""

def migrate():
    if not TARGET_POSTS.exists():
        TARGET_POSTS.mkdir(parents=True)
    if not TARGET_ASSETS.exists():
        TARGET_ASSETS.mkdir(parents=True)

    for post_dir in SOURCE_POSTS.iterdir():
        if not post_dir.is_dir():
            continue
        
        index_file = post_dir / "index.md"
        if not index_file.exists():
            continue
        
        # 读取内容
        content_raw = index_file.read_text(encoding="utf-8")
        
        # 分离 Frontmatter 和 Content
        parts = re.split(r'^---$', content_raw, flags=re.MULTILINE)
        if len(parts) < 3:
            continue
        
        fm_raw = parts[1]
        body = parts[2]
        
        # 解析 Frontmatter
        try:
            fm = yaml.safe_load(fm_raw)
        except:
            print(f"Failed to parse FM in {post_dir}")
            continue

        slug = fm.get("slug") or post_dir.name
        
        # 准备新元数据
        new_fm = {
            "title": fm.get("title", "Untitled"),
            "description": fm.get("description", ""),
            "pubDatetime": ensure_datetime(fm.get("date")),
            "tags": fm.get("tags", ["others"]),
            "draft": fm.get("draft", False),
            "featured": fm.get("featured", False),
            "author": fm.get("author", DEFAULT_AUTHOR)
        }

        # 处理图片迁移
        source_images = post_dir / "images"
        if source_images.exists():
            target_post_assets = TARGET_ASSETS / slug
            if not target_post_assets.exists():
                target_post_assets.mkdir(parents=True)
            
            for img in source_images.iterdir():
                if img.is_file():
                    shutil.copy2(img, target_post_assets / img.name)
            
            # 更新正文中的图片引用
            body = body.replace("images/", f"../../assets/blog/{slug}/")
            
            # 更新 ogImage (使用相对路径以适配 Astro image() helper)
            if fm.get("image"):
                img_name = Path(fm["image"]).name
                new_fm["ogImage"] = f"../../assets/blog/{slug}/{img_name}"

        # 处理正文转义（修复之前出现的 \' 问题）
        body = body.replace("\\'", "'")

        # 转换 Shortcodes (toggle)
        body = re.sub(r'\{\{<\s*toggle\s+(.*?)\s*>\}\}(.*?)\{\{<\s*/\s*toggle\s*>\}\}', 
                      transform_toggle, body, flags=re.DOTALL)

        # 写入新的 .mdx 文件
        new_fm_str = yaml.dump(new_fm, allow_unicode=True, sort_keys=False)
        output_content = f"--- \n{new_fm_str}---\n{body}"
        
        target_file = TARGET_POSTS / f"{slug}.mdx"
        target_file.write_text(output_content, encoding="utf-8")
        print(f"Migrated: {slug} -> {target_file}")

if __name__ == "__main__":
    migrate()
