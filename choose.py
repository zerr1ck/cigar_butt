import akshare as ak
import pandas as pd
import requests
import json
import time
import warnings
warnings.filterwarnings('ignore')

def get_realtime_quotes_sina_fixed():
    """从新浪财经获取实时A股行情（最终修复版）"""
    print("正在获取实时行情数据...")
    
    all_data = []
    
    # 分批获取沪深A股数据
    for page in range(1, 100):
        try:
            url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={page}&num=80&sort=code&asc=1&node=hs_a"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if not data:
                break
                
            all_data.extend(data)
            print(f"已获取第 {page} 页数据，累计 {len(all_data)} 只股票")
            
            time.sleep(0.5)
        except Exception as e:
            print(f"获取第 {page} 页失败: {e}")
            break
    
    if not all_data:
        print("❌ 无法获取实时行情数据")
        return pd.DataFrame()
    
    # 转换为 DataFrame
    df = pd.DataFrame(all_data)
    
    # 新浪财经返回的字段名
    # 'symbol': 'sz000001' 格式
    # 'pb': 市净率
    # 'per': 市盈率
    # 'mktcap': 总市值（万元）
    
    # 提取股票代码（去掉前缀 sz/sh）
    df['code'] = df['symbol'].str[2:]  # 去掉 'sz' 或 'sh' 前缀
    
    # 数据类型转换
    df['pb'] = pd.to_numeric(df['pb'], errors='coerce')
    df['per'] = pd.to_numeric(df['per'], errors='coerce')
    df['trade'] = pd.to_numeric(df['trade'], errors='coerce')
    df['mktcap'] = pd.to_numeric(df['mktcap'], errors='coerce') * 10000  # 万元转元
    
    # 重命名字段
    df = df.rename(columns={
        'name': 'name',
        'pb': 'pb_ratio',
        'per': 'pe_ratio', 
        'trade': 'price',
        'mktcap': 'market_cap'
    })
    
    # 过滤有效数据
    df = df.dropna(subset=['pb_ratio', 'price'])
    df = df[df['pb_ratio'] > 0]
    df = df[df['price'] > 0]
    
    print(f"📊 成功获取 {len(df)} 只股票的有效行情数据")
    print(f"📊 PB 数据范围: {df['pb_ratio'].min():.3f} ~ {df['pb_ratio'].max():.3f}")
    
    return df[['code', 'name', 'price', 'pb_ratio', 'pe_ratio', 'market_cap']]

def get_stock_list_offline():
    """获取股票列表（本地缓存）"""
    try:
        df = pd.read_csv('a_stock_list.csv', dtype={'code': str})
        print(f"✅ 从本地加载 {len(df)} 只股票")
    except:
        print("正在获取股票列表并保存...")
        df = ak.stock_info_a_code_name()
        df = df[~df['name'].str.contains('ST|退', na=False)]
        df['code'] = df['code'].astype(str).str.zfill(6)
        df = df[df['code'].str.startswith(('60', '00'))]  # 只保留主板
        df.to_csv('a_stock_list.csv', index=False, encoding='utf-8')
        print(f"✅ 已保存 {len(df)} 只股票到本地")
    
    return df

def get_cigar_butt_realtime_final():
    """实时捡烟蒂策略（最终版）"""
    print("🔍 开始执行捡烟蒂策略...")
    
    # 获取实时行情
    realtime_data = get_realtime_quotes_sina_fixed()
    if realtime_data.empty:
        print("❌ 获取实时行情失败")
        return pd.DataFrame()
    
    print(f"📊 从新浪财经获取到 {len(realtime_data)} 只股票数据")
    
    # 获取股票列表
    stock_list = get_stock_list_offline()
    
    # 标准化股票代码格式
    realtime_data['code'] = realtime_data['code'].astype(str).str.zfill(6)
    stock_list['code'] = stock_list['code'].astype(str).str.zfill(6)
    
    # 合并数据（只保留非ST股票）
    merged = pd.merge(
        realtime_data,
        stock_list[['code', 'name']].rename(columns={'name': 'display_name'}),
        on='code', how='inner'
    )
    
    print(f"📊 合并后数据 {len(merged)} 条")
    
    # 捡烟蒂筛选条件
    candidates = merged[
        (merged['pb_ratio'] > 0) & (merged['pb_ratio'] <= 1.2) &  # PB <= 1.2
        (merged['pe_ratio'] > 0) & (merged['pe_ratio'] <= 20) &   # PE <= 20
        (merged['market_cap'] > 1e10) &                          # 市值 > 100亿
        (merged['price'] > 0)                                    # 股价 > 0
    ].copy()
    
    if not candidates.empty:
        result = candidates[['display_name', 'code', 'price', 'pb_ratio', 'pe_ratio', 'market_cap']].copy()
        result = result.sort_values('pb_ratio').reset_index(drop=True)
        result['market_cap'] = (result['market_cap'] / 1e8).round(2)  # 转为亿元
        result.columns = ['股票名', '代码', '股价', 'PB', 'PE', '市值(亿)']
        
        print(f"\n✅ 找到 {len(result)} 只捡烟蒂候选股（PB≤1.2）:")
        print(result.to_string(index=False))
        
        return result
    else:
        print("❌ 未找到 PB≤1.2 的股票")
        
        # 显示 PB 最低的股票
        lowest = merged.nsmallest(20, 'pb_ratio')[['display_name', 'code', 'price', 'pb_ratio', 'pe_ratio', 'market_cap']].copy()
        lowest['market_cap'] = (lowest['market_cap'] / 1e8).round(2)
        lowest.columns = ['股票名', '代码', '股价', 'PB', 'PE', '市值(亿)']
        
        print(f"\n📊 PB 最低的 20 只股票:")
        print(lowest.to_string(index=False))
        
        return pd.DataFrame()

if __name__ == "__main__":
    start_time = time.time()
    candidates = get_cigar_butt_realtime_final()
    print(f"\n⏱️ 总耗时: {round(time.time() - start_time, 2)} 秒")
    
    # 保存结果
    if not candidates.empty:
        candidates.to_csv('cigar_butt_realtime.csv', index=False, encoding='utf-8')
        print("✅ 结果已保存到 cigar_butt_realtime.csv")