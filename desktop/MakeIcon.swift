import AppKit

let directory = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
for size in [16, 32, 64, 128, 256, 512, 1024] {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
                                  bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                  isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    let s = CGFloat(size)
    let bounds = NSRect(x: s * 0.055, y: s * 0.055, width: s * 0.89, height: s * 0.89)
    let background = NSBezierPath(roundedRect: bounds, xRadius: s * 0.20, yRadius: s * 0.20)
    NSGradient(colors: [NSColor(calibratedRed: 0.19, green: 0.13, blue: 0.33, alpha: 1),
                        NSColor(calibratedRed: 0.06, green: 0.065, blue: 0.12, alpha: 1)])!.draw(in: background, angle: 55)
    let heights: [CGFloat] = [0.15, 0.29, 0.47, 0.62, 0.39, 0.22, 0.12]
    for (i, height) in heights.enumerated() {
        let rect = NSRect(x: s * (0.22 + CGFloat(i) * 0.086), y: s * (0.5 - height / 2),
                          width: s * 0.036, height: s * height)
        NSColor(calibratedRed: 0.70 + CGFloat(i) * 0.02, green: 0.57 + CGFloat(i) * 0.035, blue: 1, alpha: 1).setFill()
        NSBezierPath(roundedRect: rect, xRadius: s * 0.018, yRadius: s * 0.018).fill()
    }
    NSGraphicsContext.restoreGraphicsState()
    let data = bitmap.representation(using: .png, properties: [:])!
    if size <= 512 {
        try data.write(to: directory.appendingPathComponent("icon_\(size)x\(size).png"))
    }
    if size >= 32 {
        let half = size / 2
        try data.write(to: directory.appendingPathComponent("icon_\(half)x\(half)@2x.png"))
    }
}
