from pinecone import Pinecone

pc = Pinecone(api_key="pcsk_6uBZho_2Kks6582ewJFBQX3m6kttDNh4Tgc4uSgPLqLqgCYAiCFaZ7fi1DGL17DfUx9ify")
index = pc.Index("food-safety")

target_namespace = "chocolate"

# 1. جلب قائمة المعرفات
list_results = index.list_paginated(namespace=target_namespace, limit=5)
ids = [v.id for v in list_results.vectors]

if not ids:
    print("❌ لا توجد أي IDs في هذا الـ Namespace!")
else:
    # 2. جلب البيانات باستخدام fetch
    fetch_results = index.fetch(ids=ids, namespace=target_namespace)
    
    print("\n--- تحليل الـ Metadata الفعلي ---")
    for v_id in ids:
        # الوصول للبيانات كخاصية Object Attribute
        if v_id in fetch_results.vectors:
            vector_obj = fetch_results.vectors[v_id]
            
            # هنا التعديل: الوصول المباشر للـ metadata
            if hasattr(vector_obj, 'metadata') and vector_obj.metadata:
                metadata = vector_obj.metadata
                print(f"ID: {v_id}")
                print(f"Metadata المسترجع: {metadata}")
            else:
                print(f"ID: {v_id} -> لا يحتوي على metadata")
            print("-" * 30)