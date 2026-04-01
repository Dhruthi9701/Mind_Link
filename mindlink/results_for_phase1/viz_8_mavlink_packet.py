"""Generate MAVLink Packet Structure"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.style.use('dark_background')

print("Generating MAVLink Packet Structure...")

fig, ax = plt.subplots(figsize=(16, 6))
fig.patch.set_facecolor('#080A14')

# Packet structure
packet_fields = [
    ('STX\n0xFE', 1, '#FF6B6B', 'Start'),
    ('LEN\n18', 1, '#4ECDC4', 'Length'),
    ('SEQ', 1, '#45B7D1', 'Sequence'),
    ('SYS\n1', 1, '#96CEB4', 'System ID'),
    ('COMP\n1', 1, '#FFEAA7', 'Component'),
    ('MSG\n70', 1, '#DFE6E9', 'Message ID'),
    ('PAYLOAD\n(RC Channels)', 12, '#74B9FF', 'Data'),
    ('CRC', 2, '#A29BFE', 'Checksum')
]

x_offset = 0
for field, width, color, desc in packet_fields:
    rect = patches.Rectangle((x_offset, 0), width, 1, linewidth=3, 
                             edgecolor='white', facecolor=color, alpha=0.8)
    ax.add_patch(rect)
    
    # Field name
    ax.text(x_offset + width/2, 0.5, field, ha='center', va='center', 
           fontsize=11 if width > 1 else 10, fontweight='bold', color='black')
    
    # Description below
    ax.text(x_offset + width/2, -0.3, desc, ha='center', va='top', 
           fontsize=9, color='white', style='italic')
    
    # Byte count above
    ax.text(x_offset + width/2, 1.3, f'{width} byte{"s" if width > 1 else ""}', 
           ha='center', va='bottom', fontsize=9, color='white')
    
    x_offset += width

ax.set_xlim(-0.5, x_offset + 0.5)
ax.set_ylim(-0.8, 1.8)
ax.axis('off')
ax.set_title('MAVLink RC_CHANNELS_OVERRIDE Packet Structure (Message ID: 70)', 
            fontsize=16, fontweight='bold', pad=30, color='white')

# Add total size
ax.text(x_offset/2, -0.6, f'Total Packet Size: {x_offset} bytes', 
       ha='center', fontsize=12, fontweight='bold', color='#FFDC00',
       bbox=dict(boxstyle='round', facecolor='#FFDC00', alpha=0.3))

plt.tight_layout()
plt.savefig('5_protocol_synthesis/mavlink_packet_structure.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: mavlink_packet_structure.png")
plt.close()
