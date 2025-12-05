import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged, User } from 'firebase/auth';
import { 
  getFirestore, 
  collection, 
  addDoc, 
  updateDoc, 
  doc, 
  onSnapshot, 
  query, 
  orderBy, 
  serverTimestamp 
} from 'firebase/firestore';
import { Search, RotateCcw, Plus, Package, Archive, AlertCircle } from 'lucide-react';

// --- Firebase Configuration ---
const firebaseConfig = JSON.parse(__firebase_config);
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

// --- Types ---
interface Item {
  id: string;
  itemId: number;
  name: string;
  isbn: string;
  publisher: string;
  stock: number;
  alert: number;
  location: string;
}

interface Log {
  id: string;
  date: any;
  action: string;
  itemId: number;
  itemName: string;
  change: number;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [view, setView] = useState<'list' | 'add'>('list');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Selection State
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [qty, setQty] = useState(1);

  // Add Item Form State
  const [newItem, setNewItem] = useState({
    name: '',
    publisher: '',
    isbn: '',
    location: '',
    stock: 1,
    alert: 5
  });

  // --- Auth & Data Fetching ---
  useEffect(() => {
    const initAuth = async () => {
      if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
         // Custom token handling if needed
      } else {
        await signInAnonymously(auth);
      }
    };
    initAuth();
    const unsubscribe = onAuthStateChanged(auth, setUser);
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (!user) return;

    // Fetch Items
    const itemsRef = collection(db, 'artifacts', appId, 'public', 'data', 'textbook_items');
    const unsubscribeItems = onSnapshot(itemsRef, (snapshot) => {
      const itemsData = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() } as Item));
      // Sort manually since simple query required
      itemsData.sort((a, b) => a.itemId - b.itemId);
      setItems(itemsData);
    }, (error) => console.error("Error items:", error));

    return () => {
      unsubscribeItems();
    };
  }, [user]);

  // --- Handlers ---

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !newItem.name || !newItem.publisher) return;

    const maxId = items.length > 0 ? Math.max(...items.map(i => i.itemId)) : 0;
    const nextId = maxId + 1;

    try {
      // Add Item
      await addDoc(collection(db, 'artifacts', appId, 'public', 'data', 'textbook_items'), {
        itemId: nextId,
        name: newItem.name,
        isbn: newItem.isbn,
        publisher: newItem.publisher,
        stock: newItem.stock,
        alert: newItem.alert,
        location: newItem.location,
        createdAt: serverTimestamp()
      });

      // Add Log
      await addDoc(collection(db, 'artifacts', appId, 'public', 'data', 'textbook_logs'), {
        date: serverTimestamp(),
        action: '新規登録',
        itemId: nextId,
        itemName: newItem.name,
        change: newItem.stock
      });

      alert(`登録完了: ${newItem.name}`);
      setNewItem({ name: '', publisher: '', isbn: '', location: '', stock: 1, alert: 5 });
      setView('list');
    } catch (err) {
      console.error(err);
      alert("エラーが発生しました");
    }
  };

  const handleStockUpdate = async (type: '入庫' | '出庫') => {
    if (!user || !selectedItemId) return;

    const item = items.find(i => i.id === selectedItemId);
    if (!item) return;

    const change = type === '入庫' ? qty : -qty;
    const newStock = item.stock + change;

    if (newStock < 0) {
      alert("在庫不足です");
      return;
    }

    try {
      // Update Item
      await updateDoc(doc(db, 'artifacts', appId, 'public', 'data', 'textbook_items', selectedItemId), {
        stock: newStock
      });

      // Add Log
      await addDoc(collection(db, 'artifacts', appId, 'public', 'data', 'textbook_logs'), {
        date: serverTimestamp(),
        action: type,
        itemId: item.itemId,
        itemName: item.name,
        change: change
      });

      // Reset Qty but keep selection? Or mimic behavior provided: toast & stay
      // We will mimic the behavior (rerun equivalent)
    } catch (err) {
      console.error(err);
      alert("更新エラー");
    }
  };

  const filteredItems = items.filter(item => 
    searchQuery === '' || 
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.publisher.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedItem = items.find(i => i.id === selectedItemId);

  // --- Styles mimicking the user's CSS ---
  // Container style for mobile optimization
  const containerClass = "max-w-[600px] mx-auto bg-white min-h-screen shadow-lg relative pb-32 font-sans text-gray-800";
  
  // ★修正箇所：ヘッダーをよりコンパクトに（py-2 -> py-1, text-[11px] -> text-[10px]）
  const headerBoxClass = "bg-[#222] text-white font-bold text-[10px] text-center py-1 px-1 rounded block w-full leading-tight flex items-center justify-center";
  
  return (
    <div className="bg-gray-100 min-h-screen p-0 sm:p-4">
      <div className={containerClass}>
        
        {/* Header */}
        <div className="p-4 border-b">
          <h3 className="text-xl font-bold mb-4">教科書在庫管理</h3>
          
          {/* Menu / Tabs */}
          <div className="flex gap-2 p-1 bg-gray-100 rounded-lg">
            <button 
              onClick={() => setView('list')}
              className={`flex-1 py-2 text-sm font-bold rounded-md transition-all ${view === 'list' ? 'bg-white shadow text-gray-800' : 'text-gray-500 hover:bg-gray-200'}`}
            >
              在庫リスト
            </button>
            <button 
              onClick={() => setView('add')}
              className={`flex-1 py-2 text-sm font-bold rounded-md transition-all flex items-center justify-center gap-1 ${view === 'add' ? 'bg-white shadow text-gray-800' : 'text-gray-500 hover:bg-gray-200'}`}
            >
              <Plus size={14} /> 教科書を追加
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-2">
          
          {view === 'list' && (
            <>
              {/* Search & Refresh */}
              <div className="flex gap-2 mb-4">
                <div className="relative flex-grow">
                  <Search className="absolute left-2 top-2.5 text-gray-400" size={16} />
                  <input 
                    type="text" 
                    placeholder="検索..." 
                    className="w-full pl-8 pr-2 py-2 border rounded text-sm focus:outline-none focus:border-blue-500"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <button 
                  onClick={() => { setSearchQuery(''); setSelectedItemId(null); }}
                  className="px-4 border rounded bg-white hover:bg-gray-50 text-sm font-bold text-gray-600 flex items-center gap-1"
                >
                  <RotateCcw size={14} /> 更新
                </button>
              </div>

              {/* Table Header */}
              <div className="flex gap-1 mb-2">
                <div className={`${headerBoxClass} w-[70%]`}>教科書名 (タップして選択)</div>
                <div className={`${headerBoxClass} w-[30%]`}>在庫</div>
              </div>

              {/* List Items */}
              <div className="flex flex-col gap-0">
                {filteredItems.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 text-sm">データがありません</div>
                ) : (
                  filteredItems.map((item) => {
                    const isSelected = selectedItemId === item.id;
                    const isLow = item.stock <= item.alert;
                    
                    return (
                      <div key={item.id} className="group">
                        <div className="flex gap-1 py-1 items-stretch">
                          {/* Name Button */}
                          <div className="w-[70%] pl-1">
                            <button
                              onClick={() => setSelectedItemId(item.id)}
                              className={`
                                w-full text-left font-bold text-[13px] min-h-[42px] px-2 py-1 rounded border border-gray-200 leading-tight transition-all
                                ${isSelected ? 'bg-green-50 border-green-500 ring-1 ring-green-500' : 'bg-white hover:border-gray-300'}
                              `}
                            >
                              {item.name}
                              <div className="text-[10px] font-normal text-gray-500 mt-1 truncate">
                                {item.publisher} / {item.location}
                              </div>
                            </button>
                          </div>
                          
                          {/* Stock Display */}
                          <div className="w-[30%] pr-1">
                            <div className="h-full flex items-center justify-center bg-transparent">
                              <span className={`text-base ${isLow ? 'font-bold text-[#e74c3c]' : 'font-bold text-[#333]'}`}>
                                {item.stock}
                              </span>
                              {isLow && <AlertCircle size={12} className="text-[#e74c3c] ml-1" />}
                            </div>
                          </div>
                        </div>
                        <hr className="border-t border-gray-100 my-0" />
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}

          {view === 'add' && (
            <div className="p-2">
              <h5 className="font-bold mb-4 text-lg">新規登録</h5>
              <form onSubmit={handleAddItem} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 mb-1">教科書名 *</label>
                  <input 
                    required
                    type="text" 
                    className="w-full border p-2 rounded focus:outline-blue-500"
                    value={newItem.name}
                    onChange={e => setNewItem({...newItem, name: e.target.value})}
                    placeholder="例: 高校数学I"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 mb-1">出版社 *</label>
                  <input 
                    required
                    type="text" 
                    className="w-full border p-2 rounded focus:outline-blue-500"
                    value={newItem.publisher}
                    onChange={e => setNewItem({...newItem, publisher: e.target.value})}
                    placeholder="例: 数研出版"
                  />
                </div>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-gray-500 mb-1">ISBN</label>
                    <input 
                      type="text" 
                      className="w-full border p-2 rounded focus:outline-blue-500"
                      value={newItem.isbn}
                      onChange={e => setNewItem({...newItem, isbn: e.target.value})}
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-gray-500 mb-1">保管場所</label>
                    <input 
                      type="text" 
                      className="w-full border p-2 rounded focus:outline-blue-500"
                      value={newItem.location}
                      onChange={e => setNewItem({...newItem, location: e.target.value})}
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-gray-500 mb-1">初期在庫</label>
                    <input 
                      type="number" 
                      min="0"
                      className="w-full border p-2 rounded focus:outline-blue-500"
                      value={newItem.stock}
                      onChange={e => setNewItem({...newItem, stock: parseInt(e.target.value)})}
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-gray-500 mb-1">発注点</label>
                    <input 
                      type="number" 
                      min="0"
                      className="w-full border p-2 rounded focus:outline-blue-500"
                      value={newItem.alert}
                      onChange={e => setNewItem({...newItem, alert: parseInt(e.target.value)})}
                    />
                  </div>
                </div>
                <button 
                  type="submit"
                  className="w-full bg-blue-600 text-white font-bold py-3 rounded mt-4 hover:bg-blue-700 transition-colors"
                >
                  登録
                </button>
              </form>
            </div>
          )}

        </div>

        {/* Fixed Footer Logic */}
        {view === 'list' && (
          <div className="fixed bottom-0 left-0 right-0 z-50 pointer-events-none">
            {/* Centered constraints for footer to match container */}
            <div className="max-w-[600px] mx-auto pointer-events-auto">
              <div className="bg-white border-t border-gray-300 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] p-2 pb-4">
                
                {/* 1. Info Row */}
                <div className="text-[11px] text-gray-600 mb-2 truncate px-1">
                  選択中: <b className="text-black text-sm">{selectedItem ? selectedItem.name : "（未選択）"}</b> 
                  {selectedItem && ` (在庫: ${selectedItem.stock})`}
                </div>

                {/* 2. Control Row */}
                <div className="flex gap-2 items-center">
                  {/* Quantity Input */}
                  <div className="w-[25%]">
                    <input 
                      type="number" 
                      min="1" 
                      value={qty}
                      onChange={(e) => setQty(Math.max(1, parseInt(e.target.value)))}
                      className="w-full h-[40px] text-center border rounded font-bold text-lg focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {/* IN Button */}
                  <div className="w-[37.5%]">
                    <button
                      onClick={() => handleStockUpdate('入庫')}
                      disabled={!selectedItem}
                      className={`
                        w-full h-[40px] rounded font-bold text-white text-xs sm:text-sm flex items-center justify-center gap-1
                        ${!selectedItem ? 'bg-gray-300 cursor-not-allowed' : 'bg-[#28a745] hover:bg-[#218838] active:translate-y-0.5 transition-all'}
                      `}
                    >
                      <Package size={16} /> 入庫
                    </button>
                  </div>

                  {/* OUT Button */}
                  <div className="w-[37.5%]">
                    <button
                      onClick={() => handleStockUpdate('出庫')}
                      disabled={!selectedItem}
                      className={`
                        w-full h-[40px] rounded font-bold text-white text-xs sm:text-sm flex items-center justify-center gap-1
                        ${!selectedItem ? 'bg-gray-300 cursor-not-allowed' : 'bg-[#e74c3c] hover:bg-[#c0392b] active:translate-y-0.5 transition-all'}
                      `}
                    >
                      <Archive size={16} /> 出庫
                    </button>
                  </div>
                </div>

              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
