var A=Object.defineProperty,K=Object.defineProperties;var j=Object.getOwnPropertyDescriptors;var z=Object.getOwnPropertySymbols;var B=Object.prototype.hasOwnProperty,H=Object.prototype.propertyIsEnumerable;var P=(t,e,r)=>e in t?A(t,e,{enumerable:!0,configurable:!0,writable:!0,value:r}):t[e]=r,D=(t,e)=>{for(var r in e||(e={}))B.call(e,r)&&P(t,r,e[r]);if(z)for(var r of z(e))H.call(e,r)&&P(t,r,e[r]);return t},O=(t,e)=>K(t,j(e));var f=(t,e,r)=>new Promise((i,n)=>{var o=l=>{try{s(r.next(l))}catch(u){n(u)}},a=l=>{try{s(r.throw(l))}catch(u){n(u)}},s=l=>l.done?i(l.value):Promise.resolve(l.value).then(o,a);s((r=r.apply(t,e)).next())});import{x as L,i as $,v as E,Q as R}from"./index-9mzhJeVz.js";const U="pos_itqan_drafts",W=1,_="invoices";let T=null;function M(t){if(t==null)return t;try{return JSON.parse(JSON.stringify(t))}catch(e){throw console.warn("Failed to sanitize draft data for IndexedDB storage",e),e}}function b(){return f(this,null,function*(){return T||new Promise((t,e)=>{const r=indexedDB.open(U,W);r.onerror=()=>e(r.error),r.onsuccess=()=>{T=r.result,t(T)},r.onupgradeneeded=i=>{const n=i.target.result;if(!n.objectStoreNames.contains(_)){const o=n.createObjectStore(_,{keyPath:"id",autoIncrement:!0});o.createIndex("draft_id","draft_id",{unique:!0}),o.createIndex("created_at","created_at",{unique:!1}),o.createIndex("customer","customer",{unique:!1})}}})})}function G(t){return f(this,null,function*(){const e=yield b(),r=M(t)||{},i=O(D({draft_id:`DRAFT-${Date.now()}-${Math.random().toString(36).substr(2,9)}`},r),{created_at:new Date().toISOString(),updated_at:new Date().toISOString(),is_edited:!1,edit_count:0,edit_history:[],order_status:"requested",last_edited_at:null,original_created_at:new Date().toISOString()});return new Promise((n,o)=>{const l=e.transaction([_],"readwrite").objectStore(_).add(i);l.onsuccess=()=>n(i),l.onerror=()=>o(l.error)})})}function J(t,e){return f(this,null,function*(){const r=yield b();return new Promise((i,n)=>f(this,null,function*(){var o,a,s,l;try{const u=yield F(t);if(!u)return n(new Error("Draft not found"));const h=M(e)||{},x=u.edit_history||[],w=((o=u.items)==null?void 0:o.length)>0;w&&x.push({edited_at:new Date().toISOString(),edited_by:((s=(a=window.frappe)==null?void 0:a.session)==null?void 0:s.user)||"Unknown",changes_summary:`Updated ${((l=h.items)==null?void 0:l.length)||0} items`});const S=O(D(D({},u),h),{updated_at:new Date().toISOString(),is_edited:w?!0:u.is_edited,edit_count:w?(u.edit_count||0)+1:u.edit_count,edit_history:x,last_edited_at:w?new Date().toISOString():u.last_edited_at,order_status:w?"modified":u.order_status}),p=r.transaction([_],"readwrite").objectStore(_).put(S);p.onsuccess=()=>i(S),p.onerror=()=>n(p.error)}catch(u){n(u)}}))})}function Q(){return f(this,null,function*(){const t=yield b();return new Promise((e,r)=>{const o=t.transaction([_],"readonly").objectStore(_).getAll();o.onsuccess=()=>{const a=o.result.sort((s,l)=>new Date(l.created_at)-new Date(s.created_at));e(a)},o.onerror=()=>r(o.error)})})}function F(t){return f(this,null,function*(){const e=yield b();return new Promise((r,i)=>{const s=e.transaction([_],"readonly").objectStore(_).index("draft_id").get(t);s.onsuccess=()=>r(s.result),s.onerror=()=>i(s.error)})})}function C(t){return f(this,null,function*(){const e=yield b();return new Promise((r,i)=>f(this,null,function*(){try{const n=yield F(t);if(!n)return i(new Error("Draft not found"));const s=e.transaction([_],"readwrite").objectStore(_).delete(n.id);s.onsuccess=()=>r(!0),s.onerror=()=>i(s.error)}catch(n){i(n)}}))})}function at(){return f(this,null,function*(){const t=yield b();return new Promise((e,r)=>{const o=t.transaction([_],"readwrite").objectStore(_).clear();o.onsuccess=()=>e(!0),o.onerror=()=>r(o.error)})})}function V(){return f(this,null,function*(){const t=yield b();return new Promise((e,r)=>{const o=t.transaction([_],"readonly").objectStore(_).count();o.onsuccess=()=>e(o.result),o.onerror=()=>r(o.error)})})}function Y(t,e){return f(this,null,function*(){const r=yield b();return new Promise((i,n)=>f(this,null,function*(){try{const o=yield F(t);if(!o)return n(new Error("Draft not found"));const a=O(D({},o),{order_status:e,updated_at:new Date().toISOString()}),u=r.transaction([_],"readwrite").objectStore(_).put(a);u.onsuccess=()=>i(a),u.onerror=()=>n(u.error)}catch(o){n(o)}}))})}const X=["Food","Kitchen Items","Beverages","Main Course","Appetizers","Desserts","Hot Drinks","Cold Drinks","Snacks"];function Z(t){return!t||t.length===0?[]:t.filter(e=>{const r=(e.item_group||"").toLowerCase();return X.some(i=>r.includes(i.toLowerCase()))})}function tt({tableName:t,tableNote:e,items:r,time:i=new Date,isModification:n=!1}){const o=i.toLocaleTimeString("en-US",{hour:"2-digit",minute:"2-digit",hour12:!1}),a=r.map(s=>{const l=s.quantity||s.qty||1,u=s.item_name||s.item_code,h=s.notes||s.custom_notes||"";return`
            <tr>
                <td style="font-size: 18px; font-weight: bold; padding: 4px 8px; vertical-align: top;">${l}x</td>
                <td style="font-size: 16px; padding: 4px 8px;">
                    ${u}
                    ${h?`<div style="font-size: 12px; font-style: italic; color: #555; margin-top: 2px;">📝 ${h}</div>`:""}
                </td>
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
        .table-note {
            font-size: 14px;
            font-weight: bold;
            margin: 5px 0;
            border: 1px solid #000;
            padding: 4px;
            border-radius: 4px;
            background-color: #f0f0f0;
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
    ${n?'<div class="modified-banner">🔄 MODIFIED ORDER</div>':""}
    <div class="header">
        <h1>🍳 Kitchen Order</h1>
        <div class="table-name">Table: ${t}</div>
        ${e?`<div class="table-note">NOTE: ${e}</div>`:""}
    </div>
    
    <table class="items">
        ${a}
    </table>
    
    <div class="footer">
        Time: ${o}
    </div>
</body>
</html>
    `}function et({tableName:t,tableNote:e,items:r,isModification:i=!1}){const n=Z(r);if(n.length===0)return console.log("No kitchen items to print"),!1;const o=tt({tableName:t||"N/A",tableNote:e,items:n,isModification:i}),a=document.createElement("iframe");a.style.position="absolute",a.style.width="0",a.style.height="0",a.style.border="none",a.style.left="-9999px",document.body.appendChild(a);const s=a.contentDocument||a.contentWindow.document;return s.open(),s.write(o),s.close(),a.onload=()=>{try{a.contentWindow.focus(),a.contentWindow.print()}catch(l){console.error("Kitchen print error:",l)}setTimeout(()=>{document.body.removeChild(a)},1e3)},console.log(`Kitchen order printed: ${n.length} items for Table ${t}`),!0}const rt=L("posDrafts",()=>{const{showSuccess:t,showError:e,showWarning:r}=R(),i=$(0),n=$([]);function o(){return f(this,null,function*(){try{i.value=yield V()}catch(c){console.error("Error getting drafts count:",c)}})}function a(){return f(this,null,function*(){try{n.value=yield Q(),i.value=n.value.length}catch(c){console.error("Error loading drafts:",c)}})}function s(c){return n.value.filter(d=>{const p=d.table;return p?(typeof p=="object"?p.name:p)===c:!1})}function l(c){return f(this,null,function*(){if(!c)return{can_edit:!1,reason:__("No POS Profile specified")};try{return yield E("pos_itqan.api.order_edit.can_edit_orders",{pos_profile:c})}catch(d){return console.error("Error checking edit permissions:",d),{can_edit:!1,reason:__("Failed to check permissions")}}})}function u(c){return f(this,null,function*(){try{yield Y(c,"sent_to_kitchen"),yield a()}catch(d){console.error("Error marking as sent to kitchen:",d)}})}function h(dt,lt,ut){return f(this,arguments,function*(c,d,p,y=[],q=null,m=null){if(c.length===0)return r(__("Cannot save an empty cart as draft")),null;try{const v={pos_profile:p,customer:d,items:c,applied_offers:y,table:m};let g;if(q?g=yield J(q,v):g=yield G(v),m){const I=m.name||m,k=(d==null?void 0:d.customer_name)||(d==null?void 0:d.name)||d;try{yield E("pos_itqan.api.tables.add_order_to_table",{table:I,draft_id:g.draft_id,customer:k})}catch(N){console.error("Failed to add order to table:",N)}}if(yield a(),t(__("Invoice saved as draft successfully")),m){const I=m.table_name||m.name||m,k=!!q&&g.is_edited;try{et({tableName:I,items:c,isModification:k})}catch(N){console.error("Kitchen print failed:",N)}}return g}catch(v){return console.error("Error saving draft:",v),e(__("Failed to save draft")),null}})}function x(c){return f(this,null,function*(){try{return t(__("Draft invoice loaded successfully")),{items:c.items||[],customer:c.customer,applied_offers:c.applied_offers||[],table:c.table}}catch(d){throw console.error("Error loading draft:",d),e(__("Failed to load draft")),d}})}function w(c,d=null){return f(this,null,function*(){try{if(yield C(c),d){const p=d.name||d;try{yield E("pos_itqan.api.tables.remove_order_from_table",{table:p,draft_id:c})}catch(y){console.error("Failed to remove order from table:",y)}}yield a(),t(__("Draft deleted successfully"))}catch(p){console.error("Error deleting draft:",p),e(__("Failed to delete draft"))}})}function S(c){return f(this,null,function*(){const d=s(c);for(const p of d)try{yield C(p.draft_id)}catch(y){console.error("Failed to delete draft:",p.draft_id,y)}try{yield E("pos_itqan.api.tables.update_table_status",{table:c,status:"Available",current_order:null,current_customer:null,clear_all_orders:!0})}catch(p){console.error("Failed to clear table status:",p)}yield a()})}return{draftsCount:i,drafts:n,updateDraftsCount:o,loadDrafts:a,saveDraftInvoice:h,loadDraft:x,deleteDraft:w,getDraftsForTable:s,deleteAllDraftsForTable:S,canEditOrders:l,markAsSentToKitchen:u}}),st=Object.freeze(Object.defineProperty({__proto__:null,usePOSDraftsStore:rt},Symbol.toStringTag,{value:"Module"}));export{tt as b,at as c,C as d,Q as g,st as p,rt as u};
