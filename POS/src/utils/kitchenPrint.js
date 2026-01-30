/**
 * Kitchen Order Printing Utility
 * 
 * Generates a minimal kitchen ticket and triggers browser print.
 * Shows only item name + quantity + table number for kitchen staff.
 */

/**
 * List of item groups that should be printed to kitchen
 * Can be extended or made configurable via POS Settings
 */
const KITCHEN_ITEM_GROUPS = [
    'Food',
    'Kitchen Items',
    'Beverages',
    'Main Course',
    'Appetizers',
    'Desserts',
    'Hot Drinks',
    'Cold Drinks',
    'Snacks'
];

/**
 * Filter items to only include kitchen-related items
 * @param {Array} items - Cart items
 * @returns {Array} Items that should be printed to kitchen
 */
export function filterKitchenItems(items) {
    if (!items || items.length === 0) return [];

    return items.filter(item => {
        const itemGroup = (item.item_group || '').toLowerCase();
        return KITCHEN_ITEM_GROUPS.some(group =>
            itemGroup.includes(group.toLowerCase())
        );
    });
}

/**
 * Build kitchen ticket HTML
 * @param {Object} options
 * @param {string} options.tableName - Table name/number
 * @param {Array} options.items - Kitchen items to print
 * @param {Date} options.time - Order time
 * @param {boolean} options.isModification - Whether this is a modification of existing order
 * @returns {string} HTML string for printing
 */
export function buildKitchenTicketHTML({ tableName, items, time = new Date(), isModification = false }) {
    const timeStr = time.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });

    const itemsHTML = items.map(item => {
        const qty = item.quantity || item.qty || 1;
        const name = item.item_name || item.item_code;
        return `
            <tr>
                <td style="font-size: 18px; font-weight: bold; padding: 4px 8px;">${qty}x</td>
                <td style="font-size: 16px; padding: 4px 8px;">${name}</td>
            </tr>
        `;
    }).join('');

    return `
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
    ${isModification ? '<div class="modified-banner">🔄 MODIFIED ORDER</div>' : ''}
    <div class="header">
        <h1>🍳 Kitchen Order</h1>
        <div class="table-name">Table: ${tableName}</div>
    </div>
    
    <table class="items">
        ${itemsHTML}
    </table>
    
    <div class="footer">
        Time: ${timeStr}
    </div>
</body>
</html>
    `;
}

/**
 * Print kitchen order using an invisible iframe
 * @param {Object} options
 * @param {string} options.tableName - Table name
 * @param {Array} options.items - All cart items (will be filtered for kitchen items)
 * @param {boolean} options.isModification - Whether this is a modification of existing order
 * @returns {boolean} True if print was triggered, false if no kitchen items
 */
export function printKitchenOrder({ tableName, items, isModification = false }) {
    // Filter for kitchen items only
    const kitchenItems = filterKitchenItems(items);

    if (kitchenItems.length === 0) {
        console.log('No kitchen items to print');
        return false;
    }

    // Build the ticket HTML
    const ticketHTML = buildKitchenTicketHTML({
        tableName: tableName || 'N/A',
        items: kitchenItems,
        isModification: isModification
    });

    // Create hidden iframe for printing
    const iframe = document.createElement('iframe');
    iframe.style.position = 'absolute';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = 'none';
    iframe.style.left = '-9999px';

    document.body.appendChild(iframe);

    // Write content and print
    const doc = iframe.contentDocument || iframe.contentWindow.document;
    doc.open();
    doc.write(ticketHTML);
    doc.close();

    // Wait for content to load then print
    iframe.onload = () => {
        try {
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        } catch (e) {
            console.error('Kitchen print error:', e);
        }

        // Remove iframe after print dialog closes
        setTimeout(() => {
            document.body.removeChild(iframe);
        }, 1000);
    };

    console.log(`Kitchen order printed: ${kitchenItems.length} items for Table ${tableName}`);
    return true;
}

export default {
    printKitchenOrder,
    filterKitchenItems,
    buildKitchenTicketHTML,
    KITCHEN_ITEM_GROUPS
};
