import os
def group_combine_last_lines(source_directory, output_prefix, num_groups=4):
    """
    遍历指定目录中的所有.dat文件，将每个文件的最后一行按顺序分组，
    并整合到不同的新文件中。
    参数:
    source_directory (str): 包含.dat文件的源目录路径。
    output_prefix (str):    输出文件的前缀，例如 'output' 会生成 'output_group_1.txt' 等。
    num_groups (int):       要分成的组数。
    """
    print(f"正在扫描目录: '{source_directory}'...")
    # 检查源目录是否存在
    if not os.path.isdir(source_directory):
        print(f"错误：目录 '{source_directory}' 不存在。")
        return
    # 1. 找到所有 .dat 文件
    try:
        all_files = os.listdir(source_directory)
        dat_files = [f for f in all_files if f.endswith(".dat") and os.path.isfile(os.path.join(source_directory, f))]
        
        # 2. 对文件列表进行排序，确保每次处理顺序一致
        dat_files.sort()
        
        if not dat_files:
            print("在指定目录中未找到任何 .dat 文件。")
            return
            
    except Exception as e:
        print(f"错误：读取目录时发生错误: {e}")
        return
    # 3. 创建用于存储各组最后一行的列表
    # grouped_lines[0] 存储第一组的行，grouped_lines[1] 存储第二组的行，以此类推
    grouped_lines = [[] for _ in range(num_groups)]
    files_processed_count = 0
    print(f"找到了 {len(dat_files)} 个 .dat 文件，将它们分为 {num_groups} 组进行处理...")
    # 4. 遍历排序后的文件列表，读取最后一行并分组
    for index, filename in enumerate(dat_files):
        file_path = os.path.join(source_directory, filename)
        
        try:
            # 使用高效方法读取最后一行
            with open(file_path, 'rb') as f:
                try:
                    f.seek(-2, os.SEEK_END)
                    while f.read(1) != b'\n':
                        if f.tell() == 1:
                            f.seek(0)
                            break
                        f.seek(-2, os.SEEK_CUR)
                except OSError: # 文件太小或为空
                    f.seek(0)
                
                last_line = f.readline().decode('utf-8', errors='ignore').strip()
                
            if last_line:
                # 确定当前文件属于哪个组
                group_index = index % num_groups
                grouped_lines[group_index].append(last_line)
                files_processed_count += 1
                # 为了方便用户理解，显示组号为 1-4 而不是 0-3
                print(f"  [成功] 读取: {filename} -> 分配到组 {group_index + 1}")
            else:
                print(f"  [警告] 文件 '{filename}' 最后一行是空的，已跳过。")
        except Exception as e:
            print(f"  [错误] 处理文件 '{filename}' 失败: {e}")
    # 5. 将每个组的内容写入对应的输出文件
    print("\n--- 开始写入输出文件 ---")
    total_files_written = 0
    for i, lines in enumerate(grouped_lines):
        # 如果这个组收集到了行，才创建文件
        if lines:
            group_num = i + 1
            output_filename = f"{output_prefix}_group_{group_num}.txt"
            try:
                with open(output_filename, 'w', encoding='utf-8') as f_out:
                    f_out.write('\n'.join(lines) + '\n')
                print(f"[写入成功] {len(lines)} 行数据已写入到 '{output_filename}'")
                total_files_written += 1
            except IOError as e:
                print(f"[写入失败] 无法写入文件 '{output_filename}'. 原因: {e}")
    if total_files_written > 0:
        print(f"\n处理完成！共处理了 {files_processed_count} 个文件，生成了 {total_files_written} 个分组文件。")
    else:
        print("\n处理完成，但没有找到任何有效内容可以写入文件。")

if __name__ == "__main__":
    # --- 配置区域 ---
    # 1. 设置包含 .dat 文件的目录。'.' 代表当前目录。
    SOURCE_DIR = '.' 
    # 2. 设置输出文件的【前缀】。脚本会自动添加 "_group_1.txt", "_group_2.txt" 等后缀。
    OUTPUT_PREFIX = 'combined_output'
    # 3. 设置分组的数量。
    NUM_OF_GROUPS = 4
    # --- 配置结束 ---
    group_combine_last_lines(SOURCE_DIR, OUTPUT_PREFIX, NUM_OF_GROUPS)