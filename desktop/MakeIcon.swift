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
    NSColor(calibratedRed: 0.816, green: 0.980, blue: 0.369, alpha: 1).setFill()
    background.fill()
    let heights: [CGFloat] = [0.15, 0.29, 0.47, 0.62, 0.39, 0.22, 0.12]
    for (i, height) in heights.enumerated() {
        let rect = NSRect(x: s * (0.22 + CGFloat(i) * 0.086), y: s * (0.5 - height / 2),
                          width: s * 0.036, height: s * height)
        NSColor(calibratedRed: 0.071, green: 0.078, blue: 0.075, alpha: 1).setFill()
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
