var K=Object.defineProperty,$=Object.defineProperties;var j=Object.getOwnPropertyDescriptors;var P=Object.getOwnPropertySymbols;var B=Object.prototype.hasOwnProperty,H=Object.prototype.propertyIsEnumerable;var z=(e,r,o)=>r in e?K(e,r,{enumerable:!0,configurable:!0,writable:!0,value:o}):e[r]=o,g=(e,r)=>{for(var o in r||(r={}))B.call(r,o)&&z(e,o,r[o]);if(P)for(var o of P(r))H.call(r,o)&&z(e,o,r[o]);return e},O=(e,r)=>$(e,j(r));var f=(e,r,o)=>new Promise((a,n)=>{var t=l=>{try{i(o.next(l))}catch(u){n(u)}},s=l=>{try{i(o.throw(l))}catch(u){n(u)}},i=l=>l.done?a(l.value):Promise.resolve(l.value).then(t,s);i((o=o.apply(e,r)).next())});import{x as L,i as C,v as E,Q as R}from"./index-CN6SEqXn.js";const U="pos_itqan_drafts",W=1,p="invoices";let T=null;function A(e){if(e==null)return e;try{return JSON.parse(JSON.stringify(e))}catch(r){throw console.warn("Failed to sanitize draft data for IndexedDB storage",r),r}}function h(){return f(this,null,function*(){return T||new Promise((e,r)=>{const o=indexedDB.open(U,W);o.onerror=()=>r(o.error),o.onsuccess=()=>{T=o.result,e(T)},o.onupgradeneeded=a=>{const n=a.target.result;if(!n.objectStoreNames.contains(p)){const t=n.createObjectStore(p,{keyPath:"id",autoIncrement:!0});t.createIndex("draft_id","draft_id",{unique:!0}),t.createIndex("created_at","created_at",{unique:!1}),t.createIndex("customer","customer",{unique:!1})}}})})}function G(e){return f(this,null,function*(){const r=yield h(),o=A(e)||{},a=O(g({draft_id:`DRAFT-${Date.now()}-${Math.random().toString(36).substr(2,9)}`},o),{created_at:new Date().toISOString(),updated_at:new Date().toISOString(),is_edited:!1,edit_count:0,edit_history:[],order_status:"requested",last_edited_at:null,original_created_at:new Date().toISOString()});return new Promise((n,t)=>{const l=r.transaction([p],"readwrite").objectStore(p).add(a);l.onsuccess=()=>n(a),l.onerror=()=>t(l.error)})})}function J(e,r){return f(this,null,function*(){const o=yield h();return new Promise((a,n)=>f(this,null,function*(){var t,s,i,l;try{const u=yield N(e);if(!u)return n(new Error("Draft not found"));const D=A(r)||{},S=u.edit_history||[],w=((t=u.items)==null?void 0:t.length)>0;w&&S.push({edited_at:new Date().toISOString(),edited_by:((i=(s=window.frappe)==null?void 0:s.session)==null?void 0:i.user)||"Unknown",changes_summary:`Updated ${((l=D.items)==null?void 0:l.length)||0} items`});const x=O(g(g({},u),D),{updated_at:new Date().toISOString(),is_edited:w?!0:u.is_edited,edit_count:w?(u.edit_count||0)+1:u.edit_count,edit_history:S,last_edited_at:w?new Date().toISOString():u.last_edited_at,order_status:w?"modified":u.order_status}),_=o.transaction([p],"readwrite").objectStore(p).put(x);_.onsuccess=()=>a(x),_.onerror=()=>n(_.error)}catch(u){n(u)}}))})}function Q(){return f(this,null,function*(){const e=yield h();return new Promise((r,o)=>{const t=e.transaction([p],"readonly").objectStore(p).getAll();t.onsuccess=()=>{const s=t.result.sort((i,l)=>new Date(l.created_at)-new Date(i.created_at));r(s)},t.onerror=()=>o(t.error)})})}function N(e){return f(this,null,function*(){const r=yield h();return new Promise((o,a)=>{const i=r.transaction([p],"readonly").objectStore(p).index("draft_id").get(e);i.onsuccess=()=>o(i.result),i.onerror=()=>a(i.error)})})}function M(e){return f(this,null,function*(){const r=yield h();return new Promise((o,a)=>f(this,null,function*(){try{const n=yield N(e);if(!n)return a(new Error("Draft not found"));const i=r.transaction([p],"readwrite").objectStore(p).delete(n.id);i.onsuccess=()=>o(!0),i.onerror=()=>a(i.error)}catch(n){a(n)}}))})}function at(){return f(this,null,function*(){const e=yield h();return new Promise((r,o)=>{const t=e.transaction([p],"readwrite").objectStore(p).clear();t.onsuccess=()=>r(!0),t.onerror=()=>o(t.error)})})}function V(){return f(this,null,function*(){const e=yield h();return new Promise((r,o)=>{const t=e.transaction([p],"readonly").objectStore(p).count();t.onsuccess=()=>r(t.result),t.onerror=()=>o(t.error)})})}function Y(e,r){return f(this,null,function*(){const o=yield h();return new Promise((a,n)=>f(this,null,function*(){try{const t=yield N(e);if(!t)return n(new Error("Draft not found"));const s=O(g({},t),{order_status:r,updated_at:new Date().toISOString()}),u=o.transaction([p],"readwrite").objectStore(p).put(s);u.onsuccess=()=>a(s),u.onerror=()=>n(u.error)}catch(t){n(t)}}))})}const X=["Food","Kitchen Items","Beverages","Main Course","Appetizers","Desserts","Hot Drinks","Cold Drinks","Snacks"];function Z(e){return!e||e.length===0?[]:e.filter(r=>{const o=(r.item_group||"").toLowerCase();return X.some(a=>o.includes(a.toLowerCase()))})}function tt({tableName:e,items:r,time:o=new Date,isModification:a=!1}){const n=o.toLocaleTimeString("en-US",{hour:"2-digit",minute:"2-digit",hour12:!1}),t=r.map(s=>{const i=s.quantity||s.qty||1,l=s.item_name||s.item_code;return`
            <tr>
                <td style="font-size: 18px; font-weight: bold; padding: 4px 8px;">${i}x</td>
                <td style="font-size: 16px; padding: 4px 8px;">${l}</td>
            </tr>
        `}).join("");return`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kitchen Order</title>
    <style>
        @page { 
            size: 80mm auto;
            margin: 5mm;
        }
        body {
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 10px;
            width: 80mm;
            background: white;
        }
        .header {
            text-align: center;
            border-bottom: 2px dashed #000;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }
        .header h1 {
            font-size: 20px;
            margin: 0 0 5px 0;
            text-transform: uppercase;
        }
        .table-name {
            font-size: 24px;
            font-weight: bold;
            margin: 5px 0;
        }
        .items {
            width: 100%;
            border-collapse: collapse;
        }
        .items tr {
            border-bottom: 1px dotted #ccc;
        }
        .footer {
            text-align: center;
            border-top: 2px dashed #000;
            padding-top: 10px;
            margin-top: 10px;
            font-size: 12px;
        }
        .modified-banner {
            background: #FFD700;
            color: #000;
            font-size: 18px;
            font-weight: bold;
            padding: 8px;
            text-align: center;
            margin-bottom: 10px;
        }
        @media print {
            body { -webkit-print-color-adjust: exact; }
        }
    </style>
</head>
<body>
    ${a?'<div class="modified-banner">🔄 MODIFIED ORDER</div>':""}
    <div class="header">
        <h1>🍳 Kitchen Order</h1>
        <div class="table-name">Table: ${e}</div>
    </div>
    
    <table class="items">
        ${t}
    </table>
    
    <div class="footer">
        Time: ${n}
    </div>
</body>
</html>
    `}function et({tableName:e,items:r,isModification:o=!1}){const a=Z(r);if(a.length===0)return console.log("No kitchen items to print"),!1;const n=tt({tableName:e||"N/A",items:a,isModification:o}),t=document.createElement("iframe");t.style.position="absolute",t.style.width="0",t.style.height="0",t.style.border="none",t.style.left="-9999px",document.body.appendChild(t);const s=t.contentDocument||t.contentWindow.document;return s.open(),s.write(n),s.close(),t.onload=()=>{try{t.contentWindow.focus(),t.contentWindow.print()}catch(i){console.error("Kitchen print error:",i)}setTimeout(()=>{document.body.removeChild(t)},1e3)},console.log(`Kitchen order printed: ${a.length} items for Table ${e}`),!0}const rt=L("posDrafts",()=>{const{showSuccess:e,showError:r,showWarning:o}=R(),a=C(0),n=C([]);function t(){return f(this,null,function*(){try{a.value=yield V()}catch(c){console.error("Error getting drafts count:",c)}})}function s(){return f(this,null,function*(){try{n.value=yield Q(),a.value=n.value.length}catch(c){console.error("Error loading drafts:",c)}})}function i(c){return n.value.filter(d=>{const _=d.table;return _?(typeof _=="object"?_.name:_)===c:!1})}function l(c){return f(this,null,function*(){if(!c)return{can_edit:!1,reason:__("No POS Profile specified")};try{return yield E("pos_itqan.api.order_edit.can_edit_orders",{pos_profile:c})}catch(d){return console.error("Error checking edit permissions:",d),{can_edit:!1,reason:__("Failed to check permissions")}}})}function u(c){return f(this,null,function*(){try{yield Y(c,"sent_to_kitchen"),yield s()}catch(d){console.error("Error marking as sent to kitchen:",d)}})}function D(dt,lt,ut){return f(this,arguments,function*(c,d,_,b=[],q=null,m=null){if(c.length===0)return o(__("Cannot save an empty cart as draft")),null;try{const v={pos_profile:_,customer:d,items:c,applied_offers:b,table:m};let y;if(q?y=yield J(q,v):y=yield G(v),m){const I=m.name||m,k=(d==null?void 0:d.customer_name)||(d==null?void 0:d.name)||d;try{yield E("pos_itqan.api.tables.add_order_to_table",{table:I,draft_id:y.draft_id,customer:k})}catch(F){console.error("Failed to add order to table:",F)}}if(yield s(),e(__("Invoice saved as draft successfully")),m){const I=m.table_name||m.name||m,k=!!q&&y.is_edited;try{et({tableName:I,items:c,isModification:k})}catch(F){console.error("Kitchen print failed:",F)}}return y}catch(v){return console.error("Error saving draft:",v),r(__("Failed to save draft")),null}})}function S(c){return f(this,null,function*(){try{return e(__("Draft invoice loaded successfully")),{items:c.items||[],customer:c.customer,applied_offers:c.applied_offers||[],table:c.table}}catch(d){throw console.error("Error loading draft:",d),r(__("Failed to load draft")),d}})}function w(c,d=null){return f(this,null,function*(){try{if(yield M(c),d){const _=d.name||d;try{yield E("pos_itqan.api.tables.remove_order_from_table",{table:_,draft_id:c})}catch(b){console.error("Failed to remove order from table:",b)}}yield s(),e(__("Draft deleted successfully"))}catch(_){console.error("Error deleting draft:",_),r(__("Failed to delete draft"))}})}function x(c){return f(this,null,function*(){const d=i(c);for(const _ of d)try{yield M(_.draft_id)}catch(b){console.error("Failed to delete draft:",_.draft_id,b)}try{yield E("pos_itqan.api.tables.update_table_status",{table:c,status:"Available",current_order:null,current_customer:null,clear_all_orders:!0})}catch(_){console.error("Failed to clear table status:",_)}yield s()})}return{draftsCount:a,drafts:n,updateDraftsCount:t,loadDrafts:s,saveDraftInvoice:D,loadDraft:S,deleteDraft:w,getDraftsForTable:i,deleteAllDraftsForTable:x,canEditOrders:l,markAsSentToKitchen:u}}),st=Object.freeze(Object.defineProperty({__proto__:null,usePOSDraftsStore:rt},Symbol.toStringTag,{value:"Module"}));export{at as c,M as d,Q as g,st as p,rt as u};
